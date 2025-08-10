# ./src/python/event_lambdas/notification_manager/logic.py
from typing import Dict, Tuple

async def process_notification(details:Dict[str,Dict]) -> Tuple[str, Dict[str,str], str]:
    body_text = ""
    html_tables = []
    text_parts = []
    file_details = details['file_details']
    for file in file_details:
        file['virusName'] = ",".join(file.get('virusName',["None"]))
        html_tables.append(await create_file_table(file))
        text_parts.append(await create_text_part(file))
    ngroup_short_name = details['short_name']
    num_files = len(details['file_details'])
    # Change wording based on number of files
    if num_files > 1:
        subject = f"CUE Security Alert: {num_files} Infected Files Detected - {ngroup_short_name}"
        text_header = f"{num_files} Infected files detected in the CUE system.\n"
        first_line = f"This is an automated notification to inform you that {num_files} files uploaded to the CUE system have been identified as malicious."
        end_line = "The files have been handled according to security protocols. No further action is required from you at this time."
    else:
        subject = f"CUE Security Alert: Infected File Detected - {ngroup_short_name}"
        text_header = "Infected file detected in the CUE system.\n"
        first_line = "This is an automated notification to inform you that a file uploaded to the CUE system has been identified as malicious."
        end_line = "The file has been handled according to security protocols. No further action is required from you at this time."
    html_details = {"files": "".join(html_tables), "header": subject, "first_line": first_line, "end_line": end_line}
    # Prepare final text
    text_footer = "Please see the HTML version of this email for full details."
    body_text = text_header + "".join(text_parts) + text_footer
    return (subject, html_details, body_text)

async def create_text_part(file_details:Dict[str,str]) -> str:
    body_text = (
        f"File Name: {file_details.get("file_name", 'N/A')}\n"
        f"Uploaded By: {file_details.get("uploader_name", 'N/A')}\n"
        f"Collection: {file_details.get("collection_name", 'N/A')}\n"
        f"File ID: {file_details.get("file_id", 'N/A')}\n\n"
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
            <td>{file_details.get("virusName", "N/A")}</td>
        </tr>
        <tr>
            <th>File ID (Key)</th>
            <td><small>{file_details.get("file_id", "N/A" )}</small></td>
        </tr>
     </table>
    """
    return table
