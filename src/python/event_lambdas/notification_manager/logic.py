# ./src/python/event_lambdas/notification_manager/logic.py
from typing import Dict, Tuple, Any, List
import structlog

logger = structlog.get_logger(__name__)
async def process_infected_scheduled_notification(infected_file_details:Dict[str,Any], providers_exceeding_threshold:List[Dict]) -> Tuple[str, Dict[str,str], str]:
    body_text = ""
    html_tables = []
    text_parts = []

    file_details = infected_file_details.get('file_details', []) # Default to empty list
    if not isinstance(file_details, list): 
        logger.warning("file_details is not a list", received_type=type(file_details))
        file_details = []
  
    for file in file_details:
        if isinstance(file, dict):

            virus_name_value = file.get('virusName') 
            # Check if it's a list or tuple (iterable sequence)
            if isinstance(virus_name_value, (list, tuple)):
                # Join if it's a non-empty list, otherwise default to "N/A"
                 processed_virus_name = ",".join(v for v in virus_name_value if v) or "N/A"
            # Check if it's None or simply missing (handled by the get)
            elif virus_name_value is None:
                 processed_virus_name = "N/A"
            # Otherwise, assume it might be a single string value or something else
            else:
                 # Convert it directly to string, just in case
                 processed_virus_name = str(virus_name_value)

            # Assign the processed string back
            file['virusName_processed'] = processed_virus_name # Use a new key to avoid type confusion later

            # Append tables/text using the original data or the processed one as needed
            html_tables.append(await create_file_table(file)) # create_file_table needs update
            text_parts.append(await create_text_part(file))
        else:
            logger.warning("Skipping invalid file detail entry", entry=file)

    ngroup_short_name = infected_file_details.get('short_name', 'Unknown Group')
    num_files = len(file_details)
    file_info_line = ""
    provider_info_line = ""

    # Change wording based on number of files
    if num_files > 1:
        subject = f"CUE Security Alert: {num_files} Infected Files Detected - {ngroup_short_name}"
        text_header = f"{num_files} Infected files detected in the CUE system.\n"
        file_info_line = f"This is an automated notification detailing {num_files} files uploaded to the CUE system that were identified as malicious within the last period."
    elif num_files == 1:
        subject = f"CUE Security Alert: Infected File Detected - {ngroup_short_name}"
        text_header = "Infected file detected in the CUE system.\n"
        file_info_line = "This is an automated notification detailing 1 file uploaded to the CUE system identified as malicious within the last period."
    else: # No new infected files
        subject = f"CUE Security Alert: Provider Threshold Report - {ngroup_short_name}"
        text_header = "Provider infected file threshold report.\n"
        file_info_line = "No new infected files were detected in the last period."

    if providers_exceeding_threshold:
        providers_html, provider_text_part = await process_providers_report(providers_exceeding_threshold)
        provider_info_line = "Additionally, the following providers exceeded the infected file upload threshold during this period."
        if not file_info_line: # If only reporting providers
             subject = f"CUE Security Alert: Providers Exceeded Infected File Threshold - {ngroup_short_name}"
             text_header = "Provider infected file threshold report.\n"
             # Try to get group name from provider details if needed
             ngroup_name_from_providers = ngroup_short_name # Placeholder, could refine
             html_details_for_name = {'ngroup_name_from_providers': ngroup_name_from_providers}

    else:
        providers_html = ""
        provider_text_part = ""

    end_line = "Infected files are handled according to security protocols. Blocked providers require manual review in the CUE Dashboard to re-enable uploads."


    html_details = {
        "files": "".join(html_tables) if html_tables else "<p>No new infected file details in this interval.</p>",
        "header": subject,
        "first_line": file_info_line,
        "provider_intro": provider_info_line, # New key for provider intro text
        "providers": providers_html, # Contains the provider table HTML
        "end_line": end_line,
        # Pass potential group name derived if only providers reported
        "ngroup_name_from_providers": html_details_for_name.get('ngroup_name_from_providers', ngroup_short_name) if 'html_details_for_name' in locals() else ngroup_short_name
    }
    
    text_footer = "Please see the HTML version of this email for full details."
    body_text = text_header + "".join(text_parts) + "\n" + provider_text_part + "\n" + text_footer # Added provider text
    
    return (subject, html_details, body_text)

async def create_text_part(file_details:Dict[str,str]) -> str:
    body_text = (
        f"File Name: {file_details.get('file_name', 'N/A')}\n"
        f"Uploaded By: {file_details.get('uploader_name', 'N/A')}\n"
        f"Uploader IP: {file_details.get('uploader_ip', 'N/A')}\n"
        f"Collection: {file_details.get('collection_name', 'N/A')}\n"
        f"Detected Threats: {file_details.get('virusName_processed', 'N/A')}\n"
        f"File ID: {file_details.get('file_id', 'N/A')}\n\n"
    )
    return body_text

async def create_file_table(file_details:Dict[str,str]) -> str:
    table = f"""
    <table>
        <tr>
            <th>File Name</th>
            <td>{file_details.get("file_name", "N/A")}</td>
        </tr>
        <tr>
            <th>Uploaded By</th>
            <td>{file_details.get("uploader_name", "N/A")}</td>
        </tr>
        <tr>
            <th>Uploader IP Address</th>
            <td>{file_details.get("uploader_ip", "N/A")}</td>
        </tr>
        <tr>
            <th>Collection</th>
            <td>{file_details.get("collection_name", "N/A")}</td>
        </tr>
        <tr>
            <th>Date Scanned</th>
            <td>{file_details.get("date_scanned", "N/A")}</td>
        </tr>
        <tr>
            <th>Scan Result</th>
            <td><strong>{file_details.get("scan_result", "N/A")}</strong></td>
        </tr>
        <tr>
            <th>Detected Threats</th>
            <td>{file_details.get("virusName_processed", "N/A")}</td>
        </tr>
        <tr>
            <th>File ID (Key)</th>
            <td><small>{file_details.get("file_id", "N/A" )}</small></td>
        </tr>
    </table>
    """
    return table

async def process_providers_report(providers_exceeding_threshold:List[Dict]) -> Tuple[str, str]:
    """Generates HTML table and text summary for providers exceeding the threshold."""
    
    provider_html = """
    <div>
        <table>
            <tr>
                <th>Provider Name</th>
                <th>Currently Blocked?</th>
                <th>Reason</th>
            </tr>
    """ 
    provider_text_parts = ["\n--- Providers Exceeding Threshold ---\n"]

    for provider in providers_exceeding_threshold:
        provider_name = provider.get("provider_name","N/A")
        is_blocked = "Yes" if provider.get("is_currently_blocked") else "No"
        reason = provider.get("current_reason") or ("-" if not provider.get("is_currently_blocked") else "Reason not recorded") # Provide more context
        
        table_row = f"""
            <tr>
                <td>{provider_name}</td>
                <td>{is_blocked}</td>
                <td>{reason}</td>
            </tr>
        """ 
        provider_html += table_row
        provider_text_parts.append(f"Provider: {provider_name}, Blocked: {is_blocked}, Reason: {reason}\n")

    provider_html += """
        </table>
        <p>Providers are blocked automatically by the system. To allow these providers to upload again, review their status and enable their "Can upload" permission in the CUE Dashboard.</p>
    </div>
    """
    
    return provider_html, "".join(provider_text_parts)
