'use client';

import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine
} from 'recharts';
import { format } from 'date-fns';

export interface ChartDataPoint {
    date: string;
    price: number;
    isPrediction: boolean;
    lowerBound?: number;
    upperBound?: number;
}

interface PredictionChartProps {
    data: ChartDataPoint[];
    symbol: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        const isPred = payload[0].payload.isPrediction;
        return (
            <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700 p-4 rounded-lg shadow-xl">
                <p className="text-slate-400 text-sm mb-1">{format(new Date(label), 'MMM dd, yyyy')}</p>
                <p className="text-2xl font-bold text-white">
                    ₹{payload[0].value.toFixed(2)}
                </p>
                {isPred && (
                    <div className="mt-2 text-xs text-primary font-medium bg-primary/10 px-2 py-1 rounded w-fit">
                        Forecasted
                    </div>
                )}
            </div>
        );
    }
    return null;
};

export function PredictionChart({ data, symbol }: PredictionChartProps) {
    // Find the start of prediction to draw a vertical line
    const predictionStartDate = data.find(d => d.isPrediction)?.date;

    return (
        <div className="w-full h-[500px] glass-card p-6 rounded-3xl">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-white">{symbol} Price Forecast</h2>
                    <p className="text-slate-400 text-sm">Historical Data + 15 Day Prediction</p>
                </div>
                {/* Legend */}
                <div className="flex gap-4 text-sm">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                        <span className="text-slate-300">Historical</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-green-500"></div>
                        <span className="text-slate-300">Prediction</span>
                    </div>
                </div>
            </div>

            <ResponsiveContainer width="100%" height="85%">
                <AreaChart
                    data={data}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
                    <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorPred" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis
                        dataKey="date"
                        stroke="#64748b"
                        tickFormatter={(str) => format(new Date(str), 'MMM dd')}
                        minTickGap={30}
                    />
                    <YAxis
                        stroke="#64748b"
                        domain={['auto', 'auto']}
                        tickFormatter={(val) => `₹${val}`}
                    />
                    <Tooltip content={<CustomTooltip />} />

                    <Area
                        type="monotone"
                        dataKey="price"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorPrice)"
                    />

                    {/* We might strictly need two separate areas or custom rendering to change color for prediction part.
              For simplicity, let's use a reference line and maybe overlaid area if we can split data.
              For now, simple single line. We can enhance this later.
          */}

                    {predictionStartDate && (
                        <ReferenceLine x={predictionStartDate} stroke="#cbd5e1" strokeDasharray="3 3" label={{ value: "Forecast Start", position: 'insideTopRight', fill: '#94a3b8' }} />
                    )}

                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
