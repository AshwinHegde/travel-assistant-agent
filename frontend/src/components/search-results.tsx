"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";

interface SearchQuery {
  origin: string;
  destination: string;
  depart_date: string;
  return_date: string;
  budget?: number;
  travelers: number;
}

interface SearchResultsProps {
  queries: SearchQuery[];
}

export function SearchResults({ queries }: SearchResultsProps) {
  if (!queries || queries.length === 0) {
    return null;
  }

  // Format date from ISO to human-readable
  const formatDate = (isoDate: string) => {
    return new Date(isoDate).toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="space-y-4 mt-6">
      <h3 className="text-xl font-medium">Travel Options</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {queries.map((query, index) => (
          <Card key={index} className="overflow-hidden">
            <CardHeader className="bg-muted pb-2">
              <CardTitle className="text-lg">
                {query.origin} → {query.destination}
              </CardTitle>
              <CardDescription>
                {formatDate(query.depart_date)} - {formatDate(query.return_date)}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-3">
              <div className="grid gap-2">
                <div className="flex justify-between text-sm">
                  <span>Trip Duration:</span>
                  <span className="font-medium">
                    {Math.round(
                      (new Date(query.return_date).getTime() -
                        new Date(query.depart_date).getTime()) /
                        (1000 * 60 * 60 * 24)
                    )}{" "}
                    days
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Travelers:</span>
                  <span className="font-medium">{query.travelers}</span>
                </div>
                {query.budget && (
                  <div className="flex justify-between text-sm">
                    <span>Budget:</span>
                    <span className="font-medium">
                      ${query.budget.toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
} 