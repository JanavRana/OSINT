import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './layout/AppLayout'
import Dashboard from './pages/Dashboard'
import Investigations from './pages/Investigations'
import InvestigationDetails from './pages/InvestigationDetails'
import Graph from './pages/Graph'
import Timeline from './pages/Timeline'
import Reports from './pages/Reports'
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="investigations" element={<Investigations />} />
          <Route path="investigations/:id" element={<InvestigationDetails />} />
          <Route path="graph" element={<Graph />} />
          <Route path="timeline" element={<Timeline />} />
          <Route path="reports" element={<Reports />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
