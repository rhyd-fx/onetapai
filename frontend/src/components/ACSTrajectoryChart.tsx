"use client";

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

export interface AcsChartPoint {
  match: string;
  acs: number;
  won?: boolean;
  agent?: string;
  map?: string;
  tier_name?: string;
}

interface Props {
  data?: AcsChartPoint[];
}

const SAMPLE: AcsChartPoint[] = [
  { match: '1', acs: 280, won: true, agent: 'Jett', map: 'Bind' },
  { match: '2', acs: 290, won: true, agent: 'Jett', map: 'Ascent' },
  { match: '3', acs: 210, won: false, agent: 'Jett', map: 'Haven' },
  { match: '4', acs: 180, won: false, agent: 'Reyna', map: 'Split' },
  { match: '5', acs: 140, won: false, agent: 'Reyna', map: 'Breeze' },
];

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isWin = data.won;
    return (
      <div className="border border-line/80 p-3 rounded-xl shadow-2xl bg-ink-900/95 backdrop-blur-md min-w-[150px] text-xs">
        <div className="flex justify-between items-center gap-4 border-b border-line/30 pb-2 mb-2">
          <span className="font-black text-white text-[10px] uppercase tracking-widest">Match #{data.match}</span>
          <span className={`px-1.5 py-0.5 rounded-md text-[9px] font-black uppercase tracking-widest ${isWin ? 'bg-emerald-400/15 text-emerald-400 border border-emerald-400/20' : 'bg-brand-red/15 text-brand-red border border-brand-red/20'}`}>
            {isWin ? 'Win' : 'Loss'}
          </span>
        </div>
        <div className="space-y-1.5">
          <div className="flex justify-between text-muted font-medium">
            <span>Combat Score:</span>
            <span className="font-extrabold text-white">{data.acs}</span>
          </div>
          {data.map && (
            <div className="flex justify-between text-muted font-medium">
              <span>Map:</span>
              <span className="font-bold text-white uppercase tracking-wider">{data.map}</span>
            </div>
          )}
          {data.agent && (
            <div className="flex justify-between text-muted font-medium">
              <span>Agent Played:</span>
              <span className="font-bold text-white">{data.agent}</span>
            </div>
          )}
          {data.tier_name && (
            <div className="flex justify-between text-muted font-medium">
              <span>Rank:</span>
              <span className="font-bold text-white uppercase">{data.tier_name}</span>
            </div>
          )}
        </div>
      </div>
    );
  }
  return null;
};

export default function ACSTrajectoryChart({ data }: Props) {
  if (data && data.length === 0) {
    return (
      <div className="h-[250px] md:h-[300px] flex items-center justify-center text-sm text-muted bg-ink-950/20 rounded-xl border border-line/20">
        No matches ingested for this player yet.
      </div>
    );
  }

  const series = data && data.length > 0 ? data : SAMPLE;

  return (
    <div className="w-full h-[250px] md:h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series} margin={{ top: 25, right: 10, left: -25, bottom: 0 }}>
          <defs>
            {/* Red Area Gradient */}
            <linearGradient id="colorAcs" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff4655" stopOpacity={0.25}/>
              <stop offset="95%" stopColor="#ff4655" stopOpacity={0.0}/>
            </linearGradient>
          </defs>
          
          <CartesianGrid strokeDasharray="3 3" stroke="#25292d" opacity={0.6} vertical={false} />
          
          <XAxis 
            dataKey="match" 
            stroke="#8b978f" 
            tick={{ fontSize: 10, fontWeight: 700 }}
            tickLine={false} 
            axisLine={false} 
            dy={8}
          />
          
          <YAxis 
            stroke="#8b978f" 
            tick={{ fontSize: 10, fontWeight: 700 }}
            tickLine={false} 
            axisLine={false} 
            dx={-8}
          />
          
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#3d464e', strokeWidth: 1, strokeDasharray: '3 3' }} />
          
          <ReferenceLine 
            y={200} 
            stroke="#ff4655" 
            strokeDasharray="4 4" 
            opacity={0.65} 
            label={{ 
              value: 'Tilt Threshold (200 ACS)', 
              fill: '#ff4655', 
              fontSize: 9, 
              fontWeight: 900,
              position: 'insideBottomLeft',
              dy: -4,
              dx: 6,
              style: { letterSpacing: '0.1em', textTransform: 'uppercase' }
            }} 
          />
          
          <Area 
            type="monotone" 
            dataKey="acs" 
            stroke="#ff4655" 
            strokeWidth={2.5} 
            fillOpacity={1} 
            fill="url(#colorAcs)"
            dot={(props) => {
              const { cx, cy, payload } = props;
              const isWin = payload.won;
              const dotColor = isWin ? '#34d399' : '#ff4655'; // Green for wins, Red for losses
              return (
                <circle 
                  key={`dot-${payload.match}`}
                  cx={cx} 
                  cy={cy} 
                  r={4} 
                  fill="#0c111d" 
                  stroke={dotColor} 
                  strokeWidth={2}
                  className="transition hover:r-6 cursor-pointer"
                />
              );
            }}
            activeDot={{ r: 5, strokeWidth: 1.5, fill: '#ffffff', stroke: '#ff4655' }} 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
