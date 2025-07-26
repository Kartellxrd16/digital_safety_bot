import os
import httpx
import base64
import asyncio
import urllib.parse

# --- Google Safe Browsing API Constants ---
GOOGLE_SAFE_BROWSING_API_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

# --- VirusTotal API Constants ---
VIRUSTOTAL_API_BASE_URL = "https://www.virustotal.com/api/v3"
VIRUSTOTAL_GUI_BASE_URL = "https://www.virustotal.com/gui/url/"

# Helper function for VirusTotal URL ID (for API and GUI links)
def get_vt_url_id(url: str) -> str:
    # VirusTotal GUI often uses base64url(url) without padding.
    # This is also commonly used as the 'id' for direct URL lookups in their API v3.
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")

async def scan_url(url: str) -> str:
    """
    Main function to scan a URL, prioritizing Google Safe Browsing,
    then falling back to VirusTotal for deeper analysis if GSB is safe.
    """
    # 1. Attempt scan with Google Safe Browsing first
    gsb_result = await scan_url_with_gsb(url)

    # If GSB found a malicious threat, return its verdict immediately
    if "DANGER!" in gsb_result or "Error:" in gsb_result:
        return gsb_result
    
    # If GSB reports it as safe, proceed to VirusTotal for deeper insights
    elif "safe" in gsb_result.lower(): # Check if GSB explicitly said it's safe
        vt_result = await scan_url_with_virustotal(url)
        # Combine GSB's initial safety verdict with VT's deeper analysis
        # For simplicity, if VT finds something, override GSB's "safe" with VT's warning.
        # If VT is also safe/inconclusive, append VT's message.
        if "DANGER!" in vt_result or "WARNING!" in vt_result:
            return vt_result # VT found something bad, so we prioritize its warning
        else:
            # If GSB says safe AND VT says safe/inconclusive, combine for a more complete picture
            return f"{gsb_result}\n\n--- VirusTotal Scan ---\n{vt_result}"
    else:
        # Fallback if GSB result is unexpected (e.g., neither DANGER nor safe, perhaps internal GSB error)
        # In this case, just run VT scan.
        return await scan_url_with_virustotal(url)

async def scan_url_with_gsb(url: str) -> str:
    """
    Scans a given URL using the Google Safe Browsing API.
    """
    api_key = os.getenv("GOOGLE_SAFE_BROWSE_API_KEY")
    if not api_key:
        return "❌ Error: Google Safe Browsing API key not configured. Cannot scan URL."

    payload = {
        "client": {
            "clientId": "your-digital-safety-bot",
            "clientVersion": "1.0.0"
        },
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": urllib.parse.quote(url, safe=':/')}]
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GOOGLE_SAFE_BROWSING_API_URL}?key={api_key}",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()

            if "matches" in result and len(result["matches"]) > 0:
                threat_types = ", ".join(sorted(list(set(m["threatType"] for m in result["matches"]))))
                return (
                    f"🚨 **DANGER! This URL is highly malicious!** 🚨\n"
                    f"Detected as: **{threat_types.replace('_', ' ').title()}** by Google Safe Browsing."
                    f"\n\n🛑 **DO NOT CLICK THIS LINK!**"
                )
            else:
                return (
                    f"✅ This URL appears **safe** according to Google Safe Browsing.\n"
                    f"No known malware, phishing, or unwanted software detected."
                )
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_detail = e.response.text
        if status_code == 400:
            return f"❌ **Invalid URL for GSB!** Check the link format. (Details: `{error_detail}`)"
        elif status_code == 403:
            return f"❌ **Access Denied (Google Safe Browsing)!** Check your API key or daily quota. (Details: `{error_detail}`)"
        elif status_code == 404:
            return "❌ Error: Invalid API endpoint or URL. Check the Safe Browsing API configuration."
        else:
            return (
                f"❌ An issue occurred with Google Safe Browsing scan (HTTP Error {status_code}). "
                f"Please try again later. (Details: `{error_detail[:150]}`...)"
            )
    except httpx.RequestError as e:
        return f"❌ I couldn't connect to Google Safe Browsing. Check internet. (Error: `{e}`)"
    except Exception as e:
        return f"❌ Unexpected error during GSB scan. (Details: `{e}`)"

async def scan_url_with_virustotal(url: str) -> str:
    """
    Scans a given URL using the VirusTotal API.
    This function is called after GSB for deeper analysis if GSB finds no immediate threats.
    """
    api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not api_key:
        print("VIRUSTOTAL_API_KEY not found in environment variables.")
        return "❌ Error: VirusTotal API key not configured for secondary scan."

    headers = {
        "x-apikey": api_key,
        "Accept": "application/json"
    }

    vt_url_id = get_vt_url_id(url)
    public_report_url = f"{VIRUSTOTAL_GUI_BASE_URL}{vt_url_id}/detection"

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            # Attempt 1: Check for existing URL report first in VT
            existing_report_url = f"{VIRUSTOTAL_API_BASE_URL}/urls/{vt_url_id}"
            report_response = await client.get(existing_report_url, headers=headers)

            if report_response.status_code == 200:
                report_json = report_response.json()
                attributes = report_json.get("data", {}).get("attributes", {})
                
                # Check if last_analysis_stats exists and contains results
                if attributes.get("last_analysis_stats"):
                    return await _process_vt_report_verdict(attributes, public_report_url)
                else:
                    # Report found but no analysis stats (e.g., just meta-info)
                    pass # Fall through to submit a new scan
            elif report_response.status_code == 404:
                # No existing report, proceed to submit for analysis
                pass
            elif report_response.status_code == 401:
                return "❌ **API Key Error (VT)!** Check your VirusTotal API key."
            elif report_response.status_code == 403:
                return "❌ **Access Denied (VT)!** VirusTotal quota exceeded."
            else:
                report_response.raise_for_status()

            # Attempt 2: Submit for a new analysis if no completed report was found
            submit_data = {"url": url}
            submit_response = await client.post(f"{VIRUSTOTAL_API_BASE_URL}/urls", headers=headers, data=submit_data)

            if submit_response.status_code == 400:
                submit_json = submit_response.json()
                error_code = submit_json.get("error", {}).get("code", "UNKNOWN_ERROR")
                error_message = submit_json.get("error", {}).get("message", "Malformed URL or API error.")

                if error_code == "InvalidArgumentError" and "canonicalize url" in error_message.lower():
                    return (
                        f"❌ **Invalid URL Format for VT!**\n"
                        f"VirusTotal couldn't process this. "
                        f"([View details]({public_report_url}))"
                    )
                elif error_code == "BadRequestError" and "Wrong URL id" in error_message:
                    # For common URLs that VT already knows deeply but doesn't re-submit easily.
                    # In this case, the existing report link is the best we can offer.
                    return (
                        f"ℹ️ VirusTotal couldn't initiate a new scan for this common URL. "
                        f"Please view its existing report: [View VT Report]({public_report_url})"
                    )
                else:
                    return (
                        f"❌ Issue submitting to VirusTotal: `{error_message}`. Try later."
                    )
            
            submit_response.raise_for_status()

            submit_json = submit_response.json()
            analysis_id = submit_json.get("data", {}).get("id")

            if not analysis_id:
                return "⚠️ Could not initiate VT scan. No analysis ID. Try again."

            # 3. Poll for the analysis report
            analysis_report_url = f"{VIRUSTOTAL_API_BASE_URL}/analyses/{analysis_id}"

            retries = 10
            initial_delay = 5
            for i in range(retries):
                current_delay = initial_delay + (i * 2)
                await asyncio.sleep(current_delay)

                report_response = await client.get(analysis_report_url, headers=headers)

                if report_response.status_code == 200:
                    report_json = report_response.json()
                    if "error" in report_json:
                        error_message = report_json["error"].get("message", "Unknown API error during report fetch.")
                        return f"❌ Error fetching VT report: `{error_message}`. Try again."

                    attributes = report_json.get("data", {}).get("attributes", {})
                    status = attributes.get("status")

                    if status == "completed":
                        return await _process_vt_report_verdict(attributes, public_report_url)
                    elif status == "queued" or status == "running":
                        if i == retries - 1:
                            return (
                                f"ℹ️ VT scan initiated. Report still processing ({status}). "
                                f"View progress: [Scan Progress]({public_report_url})"
                            )
                        continue
                    else:
                        return (
                            f"❓ VT report has unexpected status: `{status}`. "
                            f"[View full report]({public_report_url})"
                        )
                elif report_response.status_code == 404:
                    if i == retries - 1:
                        return (
                            f"ℹ️ VT scan initiated. Report still processing. "
                            f"View progress: [Scan Progress]({public_report_url})"
                        )
                    continue
                else:
                    report_response.raise_for_status()

            return (
                f"ℹ️ VT scan timed out. Report might still be processing. "
                f"Check later: [VirusTotal Report]({public_report_url})"
            )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_detail = e.response.text
            return (
                f"❌ VT scanning issue (HTTP Error {status_code}). Try again. "
                f"(Details: `{error_detail[:150]}`...)"
            )
        except httpx.RequestError as e:
            return f"❌ VT connection error. Check internet. (Error: `{e}`)"
        except Exception as e:
            return f"❌ Unexpected VT scan error. (Details: `{e}`)"

async def _process_vt_report_verdict(attributes: dict, public_report_url: str) -> str:
    """Helper to parse VirusTotal results for the verdict."""
    last_analysis_stats = attributes.get("last_analysis_stats", {})
    malicious = last_analysis_stats.get("malicious", 0)
    suspicious = last_analysis_stats.get("suspicious", 0)
    harmless = last_analysis_stats.get("harmless", 0)
    undetected = last_analysis_stats.get("undetected", 0)
    
    total_bad = malicious + suspicious

    if total_bad > 0:
        return (
            f"🚨 **DANGER! This URL is highly suspicious/malicious!** 🚨\n"
            f"VirusTotal detected **{malicious}** malicious and **{suspicious}** suspicious engines."
            f"\n\n🛑 **DO NOT CLICK THIS LINK!**"
            f"\n\n[View full report for more details]({public_report_url})"
        )
    elif harmless > 0:
        return (
            f"✅ This URL appears **safe** based on VirusTotal scan.\n"
            f"Detected by **{harmless}** engines as harmless. No threats found."
            f"\n\n[View full report]({public_report_url})"
        )
    else:
        # This covers truly undetected, or cases where stats are all zero (unknown)
        return (
            f"ℹ️ **VT Scan Inconclusive / No Threats Detected.** 🤔\n"
            f"VirusTotal did not detect immediate threats ({undetected} spaces reported undetected if applicable). "
            f"However, **exercise caution**, especially with new or unknown links. "
            f"\n\n[View details on VirusTotal]({public_report_url})"
        )