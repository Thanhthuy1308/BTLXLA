import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ROUTER_BASENAME } from "./lib/config";
import "./index.css";
createRoot(document.getElementById("app")!).render(<StrictMode><BrowserRouter basename={ROUTER_BASENAME}><App /></BrowserRouter></StrictMode>);
