"use client";

import { useEffect, useState } from "react";
import { BarChart3, Building2, FileText } from "lucide-react";

import { fetchLunchSummary, listAdminVendors, type LunchReportSummary, type Vendor } from "@/lib/api";

export default function AdminPage() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [summary, setSummary] = useState<LunchReportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listAdminVendors(), fetchLunchSummary()])
      .then(([vendorData, reportData]) => {
        setVendors(vendorData);
        setSummary(reportData);
      })
      .catch((loadError: Error) => {
        setError(loadError.message);
      });
  }, []);

  return (
    <main className="min-h-screen bg-neutral-50 px-4 py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <h1 className="mb-2">Admin Dashboard</h1>
          <p className="text-neutral-600">
            Vendor health, room outcomes, and lunch trend snapshots.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-4">
            {error}
          </div>
        )}

        {summary && (
          <div className="grid md:grid-cols-4 gap-4">
            <div className="bg-white rounded-2xl p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-primary-orange" />
                <span className="text-sm text-neutral-500">Total Rooms</span>
              </div>
              <p className="text-2xl">{summary.totalRooms}</p>
            </div>
            <div className="bg-white rounded-2xl p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-primary-green" />
                <span className="text-sm text-neutral-500">Decided Rooms</span>
              </div>
              <p className="text-2xl">{summary.decidedRooms}</p>
            </div>
            <div className="bg-white rounded-2xl p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <Building2 className="w-4 h-4 text-primary-orange" />
                <span className="text-sm text-neutral-500">Avg Decision</span>
              </div>
              <p className="text-2xl">{summary.averageDecisionMinutes.toFixed(1)}m</p>
            </div>
            <div className="bg-white rounded-2xl p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-primary-green" />
                <span className="text-sm text-neutral-500">Total Votes</span>
              </div>
              <p className="text-2xl">{summary.totalVotes}</p>
            </div>
          </div>
        )}

        <section className="bg-white rounded-2xl p-6 shadow-sm">
          <h4 className="mb-4">Vendors</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-neutral-500">
                  <th className="pb-3">Restaurant</th>
                  <th className="pb-3">Approval</th>
                  <th className="pb-3">Invoice</th>
                  <th className="pb-3">Reliability</th>
                  <th className="pb-3">Delivery SLA</th>
                </tr>
              </thead>
              <tbody>
                {vendors.map((vendor) => (
                  <tr key={vendor.id} className="border-t border-neutral-100">
                    <td className="py-3">{vendor.restaurantName}</td>
                    <td className="py-3 capitalize">{vendor.approvalStatus}</td>
                    <td className="py-3">{vendor.invoiceSupported ? "Yes" : "No"}</td>
                    <td className="py-3">{vendor.reliabilityScore.toFixed(2)}</td>
                    <td className="py-3">{vendor.deliverySlaMins ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
