"use client";

import { useEffect, useState } from "react";
import {
  FlaskConical,
  AlertTriangle,
  ShieldAlert,
  Cpu,
  Loader2,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
interface PredictionFeature {
  name: string;
  value: number;
  contribution: number;
}

interface PredictionRecordOut {
  time: string;
  api_id: string;
  endpoint: string;
  risk_score: number;
  prediction: string;
  confidence: number;
  top_features: PredictionFeature[];
}

export default function PredictionsPage() {
  const [data, setData] = useState<PredictionRecordOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPredictions();
  }, []);

  const fetchPredictions = async () => {
    try {
      setLoading(true);
      const response =
        await apiClient.get<PredictionRecordOut[]>("/predictions");
      setData(response.data);
      setError(null);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to load prediction data.",
      );
    } finally {
      setLoading(false);
    }
  };

  const getRelativeTime = (isoString: string) => {
    const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
    const daysDifference = Math.round(
      (new Date(isoString).getTime() - new Date().getTime()) /
        (1000 * 60 * 60 * 24),
    );
    return rtf.format(daysDifference, "day");
  };

  if (loading) {
    return (
      <div className="h-[calc(100vh-8rem)] w-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#5B5DFF] animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[calc(100vh-8rem)] w-full flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-[#FF5C5C] mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-[#E6EAF2]">
            Failed to load Predictions
          </h2>
          <p className="text-[#9AA3B2] mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#E6EAF2] mb-1 tracking-tight flex items-center gap-2">
            <FlaskConical className="w-6 h-6 text-[#5B5DFF]" />
            ML Failure Predictions
          </h1>
          <p className="text-[#9AA3B2] text-sm">
            Advanced machine learning engine predicting API downtime before it
            happens.
          </p>
        </div>
        <Badge
          variant="outline"
          className="bg-[#5B5DFF]/10 text-[#5B5DFF] border-[#5B5DFF]/20 px-3 py-1"
        >
          <Cpu className="w-4 h-4 mr-2" />
          Models Active
        </Badge>
      </div>

      {data.length === 0 ? (
        <Card className="bg-[#161A23]/50 backdrop-blur-sm border-[#242938]">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <ShieldAlert className="w-12 h-12 text-[#00C2A8] mb-4 opacity-70" />
            <h3 className="text-lg font-medium text-[#E6EAF2]">
              No imminent failures detected
            </h3>
            <p className="text-[#9AA3B2] mt-2 max-w-md text-center">
              Your APIs look healthy! Our ML models are constantly monitoring
              traffic patterns for anomalies.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.map((prediction, i) => (
            <Card
              key={i}
              className={`bg-[#161A23]/50 backdrop-blur-sm border-[#242938] overflow-hidden hover:border-[#5B5DFF]/30 transition-colors`}
            >
              <div
                className={`h-1 w-full ${prediction.risk_score >= 0.8 ? "bg-[#FF5C5C]" : prediction.risk_score >= 0.5 ? "bg-[#F5B74F]" : "bg-[#00C2A8]"}`}
              />
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start mb-2">
                  <Badge
                    variant="outline"
                    className={`font-mono ${prediction.risk_score >= 0.8 ? "text-[#FF5C5C] border-[#FF5C5C]/20 bg-[#FF5C5C]/10" : prediction.risk_score >= 0.5 ? "text-[#F5B74F] border-[#F5B74F]/20 bg-[#F5B74F]/10" : "text-[#00C2A8] border-[#00C2A8]/20 bg-[#00C2A8]/10"}`}
                  >
                    {(prediction.risk_score * 100).toFixed(0)}% RISK
                  </Badge>
                  <span className="text-xs text-[#9AA3B2] font-mono">
                    {getRelativeTime(prediction.time)}
                  </span>
                </div>
                <CardTitle
                  className="text-lg font-medium text-[#E6EAF2] font-mono truncate"
                  title={prediction.endpoint}
                >
                  {prediction.endpoint}
                </CardTitle>
                <div className="text-sm font-medium text-[#E6EAF2] mt-2 mb-1 flex items-center gap-2">
                  <AlertTriangle
                    className={`w-4 h-4 ${prediction.risk_score >= 0.8 ? "text-[#FF5C5C]" : "text-[#F5B74F]"}`}
                  />
                  {prediction.prediction}
                </div>
                <div className="text-xs text-[#9AA3B2]">
                  Confidence:{" "}
                  <span className="text-[#E6EAF2] font-medium">
                    {(prediction.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="pt-4 mt-2 border-t border-[#242938]">
                  <h4 className="text-xs font-semibold text-[#9AA3B2] uppercase tracking-wider mb-3">
                    Key Contributing Factors
                  </h4>
                  <div className="space-y-3">
                    {prediction.top_features?.map((feature, j) => (
                      <div key={j} className="flex flex-col gap-1">
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-[#E6EAF2] truncate pr-2 font-mono text-xs">
                            {feature.name}
                          </span>
                          <span className="text-[#9AA3B2] font-mono text-xs">
                            {feature.value.toFixed(2)}
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-[#1E232E] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-[#5B5DFF] to-[#3A8DFF] rounded-full"
                            style={{
                              width: `${Math.min(100, feature.contribution * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                    {(!prediction.top_features ||
                      prediction.top_features.length === 0) && (
                      <span className="text-sm text-[#9AA3B2] italic">
                        Black-box inference applied
                      </span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
