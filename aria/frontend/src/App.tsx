import React from 'react';
import { Layout } from './components/Layout';
import { Dashboard } from './components/Dashboard';
import { Calls } from './components/Calls';
import { LiveCalls } from './components/LiveCalls';
import { Bookings } from './components/Bookings';
import { Patients } from './components/Patients';
import { Reports } from './components/Reports';
import { Settings } from './components/Settings';
import { useStore } from './store/useStore';

function PageRenderer() {
  const { currentPage } = useStore();

  switch (currentPage) {
    case 'dashboard':  return <Dashboard />;
    case 'calls':      return <Calls />;
    case 'live-calls': return <LiveCalls />;
    case 'bookings':   return <Bookings />;
    case 'patients':   return <Patients />;
    case 'reports':    return <Reports />;
    case 'settings':   return <Settings />;
    default:           return <Dashboard />;
  }
}

export default function App() {
  return (
    <Layout>
      <PageRenderer />
    </Layout>
  );
}

