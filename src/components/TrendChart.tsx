import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TrendSeries } from '../types';

export function TrendChart({ series }: { series: TrendSeries }) {
  const { points } = series;
  // Reference band: use the most recent point's range (ranges can shift per lab).
  const latest = points[points.length - 1];
  const refLow = latest?.ref_low ?? undefined;
  const refHigh = latest?.ref_high ?? undefined;

  const data = points.map((p) => ({
    date: p.report_date,
    value: p.value,
    abnormal: p.abnormal,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 12, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" />
        <XAxis dataKey="date" stroke="var(--color-ink-soft)" fontSize={12} />
        <YAxis
          stroke="var(--color-ink-soft)"
          fontSize={12}
          domain={['auto', 'auto']}
          unit={series.unit ? ` ${series.unit}` : ''}
        />
        {refLow !== undefined && refHigh !== undefined && (
          <ReferenceArea
            y1={refLow}
            y2={refHigh}
            fill="var(--color-ok-soft)"
            fillOpacity={0.6}
            ifOverflow="extendDomain"
          />
        )}
        <Tooltip
          contentStyle={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-line)',
            borderRadius: 8,
            fontSize: 13,
          }}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="var(--color-accent)"
          strokeWidth={2}
          dot={(props) => {
            const { cx, cy, payload, index } = props;
            const abnormal = payload.abnormal as boolean;
            return (
              <circle
                key={index}
                cx={cx}
                cy={cy}
                r={abnormal ? 5 : 3.5}
                fill={abnormal ? 'var(--color-warn)' : 'var(--color-accent)'}
                stroke="var(--color-surface)"
                strokeWidth={1.5}
              />
            );
          }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
