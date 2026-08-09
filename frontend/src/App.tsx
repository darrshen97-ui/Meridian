import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { NotBuilt } from "./components/NotBuilt";
import { PageHeader } from "./components/PageHeader";
import { Shell } from "./components/Shell";
import { Loading } from "./components/States";
import { Accounts } from "./pages/Accounts";
import { Dashboard } from "./pages/Dashboard";
import { Documents } from "./pages/Documents";
import { Review } from "./pages/Review";
import { Settings } from "./pages/Settings";
import { Transactions } from "./pages/Transactions";
import { Welcome } from "./pages/Welcome";

// Placeholder pages are honest about being unbuilt (non-negotiable #6);
// each is replaced by its milestone.
function Placeholder({ title, milestone }: { title: string; milestone: number }) {
  return (
    <>
      <PageHeader title={title} />
      <NotBuilt feature={title} milestone={milestone} />
    </>
  );
}

function Gate() {
  const { me, loading } = useAuth();
  if (loading) {
    return (
      <div className="mx-auto max-w-sm px-6 py-24">
        <Loading label="Starting Meridian" />
      </div>
    );
  }
  if (!me) return <Welcome />;
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="review" element={<Review />} />
        <Route path="reconciliation"
          element={<Placeholder title="Reconciliation" milestone={10} />} />
        <Route path="documents" element={<Documents />} />
        <Route path="coach" element={<Placeholder title="Coach" milestone={11} />} />
        <Route path="budgets"
          element={<Placeholder title="Budgets & Simulator" milestone={12} />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </BrowserRouter>
  );
}
