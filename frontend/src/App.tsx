import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { NotBuilt } from "./components/NotBuilt";
import { PageHeader } from "./components/PageHeader";
import { Shell } from "./components/Shell";
import { Loading } from "./components/States";
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
        <Route index element={<Placeholder title="Dashboard" milestone={8} />} />
        <Route path="accounts" element={<Placeholder title="Accounts" milestone={8} />} />
        <Route path="transactions"
          element={<Placeholder title="Transactions" milestone={8} />} />
        <Route path="review" element={<Placeholder title="Review queue" milestone={9} />} />
        <Route path="reconciliation"
          element={<Placeholder title="Reconciliation" milestone={10} />} />
        <Route path="documents" element={<Placeholder title="Documents" milestone={8} />} />
        <Route path="coach" element={<Placeholder title="Coach" milestone={11} />} />
        <Route path="budgets"
          element={<Placeholder title="Budgets & Simulator" milestone={12} />} />
        <Route path="settings" element={<Placeholder title="Settings" milestone={9} />} />
        <Route path="*" element={<Placeholder title="Not found" milestone={8} />} />
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
