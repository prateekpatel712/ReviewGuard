/**
 * AEGIS Review Guard — Google Apps Script Web App
 * 
 * DEPLOYMENT INSTRUCTIONS:
 * 1. Open your Google Sheet where you want feedback to live.
 * 2. Click Extensions > Apps Script.
 * 3. Copy/paste this entire file into Code.gs (replacing default).
 * 4. Click Deploy > New Deployment.
 * 5. Select type "Web app".
 * 6. Set "Execute as" to "Me" and "Who has access" to "Anyone".
 * 7. Click Deploy, authorize permissions, and copy the deployed Web App URL.
 * 8. Paste that URL into SUBMIT_URL inside `feedback_form.html`'s CONFIG block.
 */

// Headers for CORS handling
const HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type"
};

/**
 * Handle HTTP OPTIONS request for CORS preflight
 */
function doOptions(e) {
  return ContentService.createTextOutput("")
    .setMimeType(ContentService.MimeType.TEXT)
    .setHeaders(HEADERS);
}

/**
 * Handle HTTP POST request from the Feedback HTML
 */
function doPost(e) {
  try {
    // Parse the incoming form-encoded payload
    let data = e.parameter;
    
    let timestamp = data.timestamp || new Date().toISOString();
    let name = data.name || "Customer";
    let email = data.email || "No Email";
    let feedback = data.feedback || "";
    let status = "Pending"; // Standard status for un-processed rows in ReviewGuard pipeline
    
    // Get Target Spreadsheet Tab 
    let spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = spreadsheet.getSheetByName("Feedback Responses");
    
    // Fallback if the tab doesn't exist yet
    if (!sheet) {
      sheet = spreadsheet.insertSheet("Feedback Responses");
      sheet.appendRow(["Timestamp", "Name", "Email", "Feedback", "Status"]);
    }
    
    // Append the row matching target schema: Timestamp | Name | Email | Feedback | Status
    sheet.appendRow([timestamp, name, email, feedback, status]);
    
    // Send success JSON response back to frontend
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Feedback cleanly recorded"
    }))
    .setMimeType(ContentService.MimeType.JSON)
    .setHeaders(HEADERS);
    
  } catch (error) {
    // Return explicit error for failing network checks
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    }))
    .setMimeType(ContentService.MimeType.JSON)
    .setHeaders(HEADERS);
  }
}
