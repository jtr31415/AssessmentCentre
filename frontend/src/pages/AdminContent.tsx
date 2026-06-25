import { useEffect, useRef, useState } from "react";
import {
  Upload,
  Trash2,
  FileText,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Paperclip,
} from "lucide-react";
import { api } from "../api/client";

type ContentFile = {
  file_key: string;
  label: string;
  category: string;
  original_filename: string;
  media_type: string;
  size_bytes: number;
  uploaded_at: string | null;
};

const CATEGORIES = [
  { value: "brief", label: "Brief" },
  { value: "data", label: "Data" },
  { value: "reference", label: "Reference" },
] as const;

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtDate(ts: string | null) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString();
}

function CategoryBadge({ category }: { category: string }) {
  const cls =
    category === "brief"
      ? "bg-brand-redbg text-brand-red border-brand-red"
      : category === "data"
      ? "bg-brand-b5 text-brand-blue border-brand-b4"
      : "bg-amber-50 text-amber-800 border-amber-300";
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${cls}`}>
      {category}
    </span>
  );
}

export default function AdminContent() {
  const [files, setFiles] = useState<ContentFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  // Upload form state
  const [label, setLabel] = useState("");
  const [category, setCategory] = useState<string>("brief");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Per-row busy state
  const [busyKey, setBusyKey] = useState("");

  async function load() {
    setLoading(true);
    setLoadError("");
    try {
      const data = await api.get("/api/admin/content");
      setFiles(data as ContentFile[]);
    } catch (err) {
      setLoadError((err as Error).message || "Failed to load content.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !label.trim()) return;
    setUploading(true);
    setUploadError("");
    setUploadSuccess("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("label", label.trim());
      form.append("category", category);
      await api.upload("/api/admin/content", form);
      setUploadSuccess(`Uploaded "${label.trim()}".`);
      setLabel("");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setTimeout(() => setUploadSuccess(""), 4000);
      await load();
    } catch (err) {
      setUploadError((err as Error).message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleReplace(fileKey: string, replacement: File) {
    setBusyKey(fileKey);
    try {
      const form = new FormData();
      form.append("file", replacement);
      await api.uploadPut(`/api/admin/content/${fileKey}`, form);
      await load();
    } catch (err) {
      setLoadError((err as Error).message || "Replace failed.");
    } finally {
      setBusyKey("");
    }
  }

  async function handleDelete(fileKey: string, fileLabel: string) {
    if (!window.confirm(`Delete "${fileLabel}"? Candidates will no longer see it.`)) return;
    setBusyKey(fileKey);
    try {
      await api.del(`/api/admin/content/${fileKey}`);
      await load();
    } catch (err) {
      setLoadError((err as Error).message || "Delete failed.");
    } finally {
      setBusyKey("");
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload card */}
      <div className="border border-brand-hair rounded-lg p-5 bg-white space-y-4 shadow-xs">
        <div className="panel-title">
          <h3 className="font-bold text-brand-blue text-sm">Upload Assessment File</h3>
        </div>
        <p className="text-xs text-brand-muted ml-4">
          Upload any file candidates should receive (brief, datasets, reference docs). Files
          appear in the candidate dashboard once their prep window unlocks.
        </p>

        <form onSubmit={handleUpload} className="ml-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="content-label"
                className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
              >
                Label
              </label>
              <input
                id="content-label"
                type="text"
                placeholder="e.g. Exercise Brief"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                className="w-full text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              />
            </div>
            <div>
              <label
                htmlFor="content-category"
                className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
              >
                Category
              </label>
              <select
                id="content-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full text-sm border border-brand-hair rounded px-3 py-2 bg-white text-brand-ink focus:outline-none focus:ring-2 focus:ring-brand-blue"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label
              htmlFor="content-file"
              className="block text-[10px] uppercase font-bold tracking-wider text-brand-muted mb-1.5"
            >
              File
            </label>
            <input
              id="content-file"
              ref={fileInputRef}
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-xs text-brand-ink file:mr-3 file:py-2 file:px-4 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-brand-b5 file:text-brand-blue hover:file:bg-brand-b4 cursor-pointer"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={uploading || !file || !label.trim()}
              className="bg-brand-blue hover:bg-opacity-90 text-white font-semibold text-xs px-4 py-2.5 rounded flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
              Upload File
            </button>
            {uploadSuccess && (
              <span className="text-xs font-semibold text-emerald-700">{uploadSuccess}</span>
            )}
            {uploadError && (
              <span className="text-xs font-semibold text-brand-red flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                {uploadError}
              </span>
            )}
          </div>
        </form>
      </div>

      {/* List card */}
      <div className="border border-brand-hair rounded-lg p-6 bg-white space-y-4 shadow-xs">
        <div className="flex items-center justify-between">
          <div className="panel-title mb-0">
            <h3 className="font-bold text-brand-blue text-sm">Content Library</h3>
          </div>
          <button
            onClick={load}
            className="px-2.5 py-1 text-[10px] font-semibold rounded border border-brand-b4 bg-brand-b5 text-brand-blue hover:bg-brand-b4 flex items-center gap-1 cursor-pointer"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12 text-brand-muted gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-brand-blue" />
            <span className="text-sm">Loading content…</span>
          </div>
        )}

        {!loading && loadError && (
          <div className="p-4 bg-brand-redbg border border-brand-red rounded flex items-center gap-3 text-brand-red text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span className="flex-1">{loadError}</span>
          </div>
        )}

        {!loading && !loadError && files.length === 0 && (
          <div className="py-12 flex flex-col items-center text-brand-muted gap-3 border border-dashed border-brand-hair rounded-lg bg-brand-b5">
            <FileText className="w-8 h-8 text-brand-b3" />
            <p className="text-sm">No content uploaded yet — add a file above.</p>
          </div>
        )}

        {!loading && !loadError && files.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-brand-b5 border-b border-brand-hair text-brand-blue font-bold">
                  <th className="p-3">Label</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Filename</th>
                  <th className="p-3">Size</th>
                  <th className="p-3">Uploaded</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-hair">
                {files.map((f) => (
                  <tr key={f.file_key} className="hover:bg-neutral-50 align-middle">
                    <td className="p-3 font-semibold text-brand-ink">{f.label}</td>
                    <td className="p-3">
                      <CategoryBadge category={f.category} />
                    </td>
                    <td className="p-3 font-mono text-[11px] text-brand-muted break-all">
                      {f.original_filename}
                    </td>
                    <td className="p-3 tabular-numbers whitespace-nowrap text-brand-ink">
                      {fmtSize(f.size_bytes)}
                    </td>
                    <td className="p-3 tabular-numbers whitespace-nowrap text-brand-muted">
                      {fmtDate(f.uploaded_at)}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-1.5">
                        <label
                          className={`px-2.5 py-1 text-[10px] font-semibold rounded border border-brand-b4 bg-brand-b5 text-brand-blue hover:bg-brand-b4 flex items-center gap-1 cursor-pointer ${
                            busyKey === f.file_key ? "opacity-40 pointer-events-none" : ""
                          }`}
                        >
                          <Paperclip className="w-3 h-3" />
                          Replace
                          <input
                            type="file"
                            className="hidden"
                            onChange={(e) => {
                              const r = e.target.files?.[0];
                              if (r) handleReplace(f.file_key, r);
                              e.target.value = "";
                            }}
                          />
                        </label>
                        <button
                          onClick={() => handleDelete(f.file_key, f.label)}
                          disabled={busyKey === f.file_key}
                          className="px-2.5 py-1 text-[10px] font-bold rounded border border-brand-red bg-brand-redbg text-brand-red hover:bg-red-100 flex items-center gap-1 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          {busyKey === f.file_key ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Trash2 className="w-3 h-3" />
                          )}
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
