import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ToastProvider } from "./components/Toast";
import { Spinner } from "./components/ui";

import Login from "./pages/Login";
import AdminHome from "./pages/admin/AdminHome";
import Materials from "./pages/admin/Materials";
import Courses from "./pages/admin/Courses";
import CourseReview from "./pages/admin/CourseReview";
import Analytics from "./pages/admin/Analytics";
import Audit from "./pages/admin/Audit";
import Catalog from "./pages/learner/Catalog";
import MyLearning from "./pages/learner/MyLearning";
import CourseView from "./pages/learner/CourseView";
import Certificates from "./pages/learner/Certificates";

function Guard({ role, children }: { role?: "admin" | "learner"; children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ display: "grid", placeItems: "center", height: "100vh" }}><Spinner label="Loading…" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role && user.role !== "admin") return <Navigate to="/catalog" replace />;
  return children;
}

function Home() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "admin" ? "/admin" : "/catalog"} replace />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Home />} />
            {/* admin */}
            <Route path="/admin" element={<Guard role="admin"><AdminHome /></Guard>} />
            <Route path="/admin/materials" element={<Guard role="admin"><Materials /></Guard>} />
            <Route path="/admin/courses" element={<Guard role="admin"><Courses /></Guard>} />
            <Route path="/admin/courses/:id" element={<Guard role="admin"><CourseReview /></Guard>} />
            <Route path="/admin/analytics" element={<Guard role="admin"><Analytics /></Guard>} />
            <Route path="/admin/audit" element={<Guard role="admin"><Audit /></Guard>} />
            {/* learner */}
            <Route path="/catalog" element={<Guard><Catalog /></Guard>} />
            <Route path="/learning" element={<Guard><MyLearning /></Guard>} />
            <Route path="/certificates" element={<Guard><Certificates /></Guard>} />
            <Route path="/courses/:id" element={<Guard><CourseView /></Guard>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
