"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import RatingScreen from "@/components/dashboardUser/RatingScreen";
import { fetchDecision } from "@/lib/api";
import { Restaurant } from "@/app/page";

export default function RatingPage() {
  const params = useParams();
  const router = useRouter();
  const roomId = params?.roomId as string;
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadWinner = async () => {
      try {
        setLoading(true);
        const decision = await fetchDecision(roomId);

        if (decision?.selectedOption) {
          const winner = decision.selectedOption;
          const winnerRestaurant: Restaurant = {
            id: winner.restaurantId || "decision",
            name: winner.restaurantName || winner.title,
            cuisine: winner.cuisine || "Mixed",
            priceRange: "$$",
            rating: Number((winner.confidence * 5).toFixed(1)),
            distance: "",
            hours: "Mon-Sun: 10:00 AM - 10:00 PM", // Default
            address: "", // Can be fetched if needed
            image: "/images/default.png",
            pickCount: 0,
            description: `Final ${decision.decisionType.replace("_", " ")} recommendation with confidence ${Math.round(decision.confidenceScore * 100)}%.`,
            menuItems: winner.dishName ? [{ name: winner.dishName, price: winner.price || 0 }] : [],
            reviews: 0,
          };
          setRestaurant(winnerRestaurant);
        } else {
          router.push('/home');
        }
      } catch (error) {
        console.error("Error fetching winner:", error);
        router.push("/home");
      } finally {
        setLoading(false);
      }
    };

    if (roomId) {
      loadWinner();
    }
  }, [roomId, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!restaurant) {
    return null;
  }

  // Navigation handler
  const handleNavigate = (screen: string) => {
    switch (screen) {
      case "home":
        router.push("/home");
        break;
      default:
        router.push("/home");
    }
  };

  return (
    <RatingScreen
      restaurant={restaurant}
      onNavigate={handleNavigate}
    />
  );
}

