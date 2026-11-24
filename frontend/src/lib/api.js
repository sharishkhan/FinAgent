export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000";

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "The document could not be processed.");
  }

  return payload;
}

export async function loadSampleDocument() {
  const response = await fetch(`${API_BASE_URL}/api/sample-document`, {
    method: "POST",
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "The sample report could not be loaded.");
  }

  return payload;
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error("Backend health check failed.");
  }
  return response.json();
}

export async function getSettings() {
  const response = await fetch(`${API_BASE_URL}/api/settings`);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "Settings could not be loaded.");
  }

  return payload;
}

export async function testConnection() {
  const response = await fetch(`${API_BASE_URL}/api/settings/test-connection`, {
    method: "POST",
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "The connection test could not be completed.");
  }

  return payload;
}

export async function getSavedDocuments() {
  const response = await fetch(`${API_BASE_URL}/api/documents`);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "Saved documents could not be loaded.");
  }

  return payload;
}

export async function getDocumentFinancials(documentId) {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/financials`);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "Financial figures could not be loaded.");
  }

  return payload;
}

export async function deleteDocument(documentId) {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}`, {
    method: "DELETE",
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "The document could not be deleted.");
  }

  return payload;
}

export async function generateSummary(documentId) {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/summary`, {
    method: "POST",
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok && response.status !== 503) {
    throw new Error(payload.error ?? "The AI summary could not be generated.");
  }

  return payload;
}

export async function askDocumentQuestion(documentId, question) {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/question`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok && response.status !== 503) {
    throw new Error(payload.error ?? "The question could not be answered.");
  }

  return payload;
}

export async function analyzeDocument(documentId, question) {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok && response.status !== 503) {
    throw new Error(payload.error ?? "The financial analysis could not be completed.");
  }

  return payload;
}

export async function getQuestionHistory(documentId) {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/questions`);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "Question history could not be loaded.");
  }

  return payload;
}

export async function getSavedResults() {
  const response = await fetch(`${API_BASE_URL}/api/results`);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "Saved results could not be loaded.");
  }

  return payload;
}

export async function getSavedResult(resultId) {
  const response = await fetch(`${API_BASE_URL}/api/results/${resultId}`);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "Saved result could not be loaded.");
  }

  return payload;
}

export async function deleteSavedResult(resultId) {
  const response = await fetch(`${API_BASE_URL}/api/results/${resultId}`, {
    method: "DELETE",
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error ?? "The saved result could not be deleted.");
  }

  return payload;
}
