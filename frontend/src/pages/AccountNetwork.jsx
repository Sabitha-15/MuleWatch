import { useMemo, useState } from "react";
import { Network, RefreshCw, Search } from "lucide-react";

const API = "http://127.0.0.1:8000/api/phase2";

const panel = {
  background: "#FFFFFF",
  border: "1px solid #D7E0EC",
  borderRadius: 12,
  padding: 18,
};

const field = {
  height: 40,
  border: "1px solid #CBD5E1",
  borderRadius: 8,
  padding: "0 10px",
  background: "#FFFFFF",
  color: "#172033",
};

const button = {
  border: "1px solid #CBD5E1",
  borderRadius: 8,
  padding: "9px 13px",
  background: "#FFFFFF",
  color: "#1D4ED8",
  fontWeight: 600,
  cursor: "pointer",
};

function readableRelationship(value = "") {
  return String(value).replaceAll("_", " ");
}

export default function AccountNetwork() {
  const [accountId, setAccountId] = useState("1");
  const [depth, setDepth] = useState("2");
  const [data, setData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadNetwork(id = accountId) {
    if (!String(id).trim()) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API}/accounts/${id}/network?max_depth=${depth}`
      );
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to load account network.");
      }

      setData(result);
    } catch (err) {
      setError(err.message);
      setData({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  }

  const layout = useMemo(() => {
    const nodes = data.nodes || [];
    const maxDepth = Math.max(1, ...nodes.map((node) => Number(node.depth)));
    const groups = Array.from({ length: maxDepth + 1 }, (_, level) =>
      nodes.filter((node) => Number(node.depth) === level)
    );

    const height = Math.max(
      460,
      ...groups.map((group) => group.length * 145 + 100)
    );

    const positions = {};

    groups.forEach((group, level) => {
      group.forEach((node, index) => {
        positions[node.account_id] = {
          x: 125 + level * 300,
          y: ((index + 1) * height) / (group.length + 1),
        };
      });
    });

    return {
      positions,
      width: 220 + maxDepth * 300,
      height,
    };
  }, [data.nodes]);

  // Globally position relationship labels, checking all account cards and labels.
  const renderedEdges = useMemo(() => {
    const nodeObstacles = (data.nodes || []).map((node) => {
      const p = layout.positions[node.account_id];
      return p ? { left: p.x - 82, right: p.x + 82, top: p.y - 46, bottom: p.y + 46 } : null;
    }).filter(Boolean);

    const edges = (data.edges || []).map((edge, index) => {
      const source = layout.positions[edge.source_account_id];
      const target = layout.positions[edge.target_account_id];
      if (!source || !target) return null;
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const ux = dx / distance;
      const uy = dy / distance;
      const start = { x: source.x + ux * 76, y: source.y + uy * 39 };
      const end = { x: target.x - ux * 76, y: target.y - uy * 39 };
      const pairKey = [edge.source_account_id, edge.target_account_id].sort().join(':');
      return { edge, index, start, end, pairKey, labelText: readableRelationship(edge.relationship_type) };
    }).filter(Boolean);

    // Separate multiple connections between the same pair with curved lanes.
    const pairGroups = new Map();
    edges.forEach((item) => {
      if (!pairGroups.has(item.pairKey)) pairGroups.set(item.pairKey, []);
      pairGroups.get(item.pairKey).push(item);
    });
    pairGroups.forEach((items) => items.forEach((item, index) => {
      const lane = index === 0 ? 0 : Math.ceil(index / 2) * (index % 2 ? 1 : -1);
      const dx = item.end.x - item.start.x;
      const dy = item.end.y - item.start.y;
      const length = Math.max(1, Math.hypot(dx, dy));
      const normal = { x: -dy / length, y: dx / length };
      const curveOffset = lane * 28;
      item.control = {
        x: (item.start.x + item.end.x) / 2 + normal.x * curveOffset,
        y: (item.start.y + item.end.y) / 2 + normal.y * curveOffset,
      };
      item.path = `M ${item.start.x} ${item.start.y} Q ${item.control.x} ${item.control.y} ${item.end.x} ${item.end.y}`;
    }));

    const placedLabels = [];
    const intersects = (a, b, padding = 7) =>
      a.left < b.right + padding && a.right > b.left - padding &&
      a.top < b.bottom + padding && a.bottom > b.top - padding;

    // Place longer labels first; each placement avoids every earlier label and node.
    [...edges].sort((a, b) => b.labelText.length - a.labelText.length).forEach((item) => {
      const width = Math.max(112, Math.min(220, item.labelText.length * 6.1 + 22));
      const height = 22;
      const candidates = [];
      const tValues = [0.5, 0.38, 0.62, 0.27, 0.73, 0.16, 0.84];
      const offsets = [0, 18, -18, 34, -34, 50, -50, 68, -68, 86, -86];
      const dx = item.end.x - item.start.x;
      const dy = item.end.y - item.start.y;
      const length = Math.max(1, Math.hypot(dx, dy));
      const normal = { x: -dy / length, y: dx / length };

      tValues.forEach((t, tIndex) => {
        const u = 1 - t;
        const point = {
          x: u * u * item.start.x + 2 * u * t * item.control.x + t * t * item.end.x,
          y: u * u * item.start.y + 2 * u * t * item.control.y + t * t * item.end.y,
        };
        offsets.forEach((offset, offsetIndex) => {
          const x = point.x + normal.x * offset;
          const y = point.y + normal.y * offset;
          const box = { left: x - width / 2, right: x + width / 2, top: y - height / 2, bottom: y + height / 2 };
          const outside = box.left < 4 || box.right > layout.width - 4 || box.top < 4 || box.bottom > layout.height - 4;
          const nodeHits = nodeObstacles.filter((n) => intersects(box, n, 5)).length;
          const labelHits = placedLabels.filter((p) => intersects(box, p, 5)).length;
          candidates.push({ x, y, box, score: (outside ? 20000 : 0) + nodeHits * 10000 + labelHits * 1000 + tIndex * 10 + offsetIndex });
        });
      });
      candidates.sort((a, b) => a.score - b.score);
      const chosen = candidates[0];
      item.label = { x: chosen.x, y: chosen.y };
      item.labelWidth = width;
      placedLabels.push(chosen.box);
    });
    return edges;
  }, [data.edges, data.nodes, layout.positions, layout.width, layout.height]);

  return (
    <section style={{ maxWidth: 1500, margin: "0 auto" }}>
      <div className="page-header">
        <div>
          <p className="page-eyebrow">PHASE 2 · RECURSIVE DATABASE ANALYSIS</p>
          <h1>Interactive Account Network</h1>
          <p className="page-description">
            Explore connected accounts using PostgreSQL recursive traversal
            with cycle prevention and configurable depth.
          </p>
        </div>

        <button
          style={button}
          onClick={() => loadNetwork()}
          disabled={loading}
        >
          <RefreshCw
            size={15}
            style={{ verticalAlign: "middle", marginRight: 6 }}
          />
          Refresh
        </button>
      </div>

      <div style={{ ...panel, marginBottom: 16 }}>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            loadNetwork();
          }}
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            alignItems: "end",
          }}
        >
          <label
            style={{
              display: "grid",
              gap: 5,
              fontSize: 11,
              color: "#64748B",
            }}
          >
            Root account ID
            <input
              style={{ ...field, width: 180 }}
              type="number"
              min="1"
              value={accountId}
              onChange={(event) => setAccountId(event.target.value)}
            />
          </label>

          <label
            style={{
              display: "grid",
              gap: 5,
              fontSize: 11,
              color: "#64748B",
            }}
          >
            Traversal depth
            <select
              style={{ ...field, width: 150 }}
              value={depth}
              onChange={(event) => setDepth(event.target.value)}
            >
              {[1, 2, 3, 4, 5].map((number) => (
                <option key={number} value={number}>
                  {number} level{number > 1 ? "s" : ""}
                </option>
              ))}
            </select>
          </label>

          <button
            style={{ ...button, background: "#1D4ED8", color: "white" }}
            type="submit"
            disabled={loading}
          >
            <Search
              size={15}
              style={{ verticalAlign: "middle", marginRight: 5 }}
            />
            Build Network
          </button>
        </form>
      </div>

      {error && (
        <div style={{ ...panel, color: "#B91C1C", marginBottom: 14 }}>
          {error}
        </div>
      )}

      <div style={panel}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
            marginBottom: 12,
          }}
        >
          <strong>
            <Network
              size={17}
              style={{ verticalAlign: "middle", marginRight: 7 }}
            />
            Account Relationship Graph
          </strong>

          <span style={{ color: "#64748B", fontSize: 12 }}>
            {data.nodes?.length || 0} accounts · {data.edges?.length || 0}{" "}
            relationships
          </span>
        </div>

        {data.nodes?.length ? (
          <div
            style={{
              overflow: "auto",
              border: "1px solid #E2E8F0",
              borderRadius: 10,
              background: "#F8FAFC",
            }}
          >
            <svg
              width={Math.max(800, layout.width)}
              height={layout.height}
              viewBox={`0 0 ${Math.max(800, layout.width)} ${layout.height}`}
              role="img"
              aria-label="Connected account network graph"
              style={{ display: "block" }}
            >
              <defs>
                <marker
                  id="network-arrow"
                  markerWidth="8"
                  markerHeight="8"
                  refX="6"
                  refY="3"
                  orient="auto"
                  markerUnits="userSpaceOnUse"
                >
                  <path d="M0,0 L0,6 L6,3 z" fill="#8294AD" />
                </marker>
              </defs>

              {/* Draw edges first so account nodes remain visually on top. */}
              {renderedEdges.map((item) => {
                const labelText = item.labelText;
                const labelWidth = item.labelWidth;

                return (
                  <g key={item.edge.relationship_id ?? `${item.edge.source_account_id}-${item.edge.target_account_id}-${item.index}`}>
                    <path
                      d={item.path}
                      fill="none"
                      stroke="#8294AD"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      markerEnd="url(#network-arrow)"
                    />

                    <rect
                      x={item.label.x - labelWidth / 2}
                      y={item.label.y - 10}
                      width={labelWidth}
                      height="20"
                      rx="6"
                      fill="#FFFFFF"
                      stroke="#DCE5F0"
                      strokeWidth="0.8"
                    />

                    <text
                      x={item.label.x}
                      y={item.label.y + 3.5}
                      textAnchor="middle"
                      fontSize="9.5"
                      fontWeight="600"
                      letterSpacing="0.2"
                      fill="#475569"
                    >
                      {labelText}
                    </text>
                  </g>
                );
              })}

              {data.nodes.map((node) => {
                const position = layout.positions[node.account_id];
                const isRoot = Number(node.depth) === 0;

                return (
                  <g
                    key={`${node.account_id}-${node.depth}`}
                    onClick={() => {
                      setAccountId(String(node.account_id));
                      loadNetwork(node.account_id);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <rect
                      x={position.x - 74}
                      y={position.y - 38}
                      width="148"
                      height="76"
                      rx="11"
                      fill={isRoot ? "#DBEAFE" : "#FFFFFF"}
                      stroke={isRoot ? "#2563EB" : "#CBD5E1"}
                      strokeWidth={isRoot ? 2.5 : 1.5}
                    />

                    <text
                      x={position.x}
                      y={position.y - 9}
                      textAnchor="middle"
                      fontSize="12"
                      fontWeight="700"
                      fill="#172033"
                    >
                      {node.account_number}
                    </text>

                    <text
                      x={position.x}
                      y={position.y + 11}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#64748B"
                    >
                      {node.customer_name}
                    </text>

                    <text
                      x={position.x}
                      y={position.y + 27}
                      textAnchor="middle"
                      fontSize="9.5"
                      fontWeight="600"
                      fill="#2563EB"
                    >
                      {isRoot ? "ROOT ACCOUNT" : `DEPTH ${node.depth}`}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        ) : (
          <div
            style={{
              padding: 30,
              textAlign: "center",
              color: "#64748B",
            }}
          >
            {loading
              ? "Building account network..."
              : "Enter an account ID and select Build Network to view connected accounts."}
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 18,
            flexWrap: "wrap",
            marginTop: 14,
            fontSize: 11,
            color: "#64748B",
          }}
        >
          <span>Blue node: selected root account</span>
          <span>White node: connected account</span>
          <span>Click any node to make it the new root</span>
        </div>
      </div>
    </section>
  );
}
