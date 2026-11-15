import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { AppShell } from "./components/AppShell.jsx";
import { getHealth, getSavedDocuments, getSavedResults } from "./lib/api.js";
import { DashboardPage } from "./pages/DashboardPage.jsx";
import { DocumentsPage } from "./pages/DocumentsPage.jsx";
import { HomePage } from "./pages/HomePage.jsx";
import { ReportsPage } from "./pages/ReportsPage.jsx";
import { ResearchPage } from "./pages/ResearchPage.jsx";
import { ResearchAssistantPage } from "./pages/ResearchAssistantPage.jsx";
import { SettingsPage } from "./pages/SettingsPage.jsx";

const pages = {
  home: HomePage,
  dashboard: DashboardPage,
  documents: DocumentsPage,
  research: ResearchAssistantPage,
  analysis: ResearchPage,
  reports: ReportsPage,
  settings: SettingsPage,
};

export default function App() {
  const [activePage, setActivePage] = useState("home");
  const [recentDocuments, setRecentDocuments] = useState([]);
  const [systemStatus, setSystemStatus] = useState("checking");
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState("");
  const [savedResults, setSavedResults] = useState([]);
  const [resultsLoading, setResultsLoading] = useState(true);
  const [resultsError, setResultsError] = useState("");

  const Page = pages[activePage] ?? HomePage;

  function handleProcessedDocument(document) {
    setRecentDocuments((current) => [
      document,
      ...current.filter((item) => item.document_id !== document.document_id),
    ]);
  }

  async function loadSavedDocuments() {
    setDocumentsLoading(true);
    setDocumentsError("");

    try {
      const payload = await getSavedDocuments();
      setRecentDocuments(payload.documents ?? []);
    } catch (loadError) {
      setDocumentsError(loadError.message);
    } finally {
      setDocumentsLoading(false);
    }
  }

  async function loadSavedResults() {
    setResultsLoading(true);
    setResultsError("");

    try {
      const payload = await getSavedResults();
      setSavedResults(payload.results ?? []);
    } catch (loadError) {
      setResultsError(loadError.message);
    } finally {
      setResultsLoading(false);
    }
  }

  useEffect(() => {
    let isMounted = true;

    getHealth()
      .then(() => {
        if (isMounted) {
          setSystemStatus("ready");
        }
      })
      .catch(() => {
        if (isMounted) {
          setSystemStatus("offline");
        }
      });

    loadSavedDocuments();
    loadSavedResults();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <AppShell activePage={activePage} onNavigate={setActivePage} systemStatus={systemStatus}>
      <AnimatePresence mode="wait">
        <motion.div
          key={activePage}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
        >
          <Page
            recentDocuments={recentDocuments}
            documentsLoading={documentsLoading}
            documentsError={documentsError}
            savedResults={savedResults}
            resultsLoading={resultsLoading}
            resultsError={resultsError}
            systemStatus={systemStatus}
            onNavigate={setActivePage}
            onDocumentProcessed={handleProcessedDocument}
            onRefreshDocuments={loadSavedDocuments}
            onRefreshResults={loadSavedResults}
          />
        </motion.div>
      </AnimatePresence>
    </AppShell>
  );
}
