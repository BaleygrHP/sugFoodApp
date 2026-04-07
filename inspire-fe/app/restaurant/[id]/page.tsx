"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import RestaurantDetail from "@/components/dashboardUser/RestaurantDetail";
import { Restaurant, Screen } from "@/app/page";
import { fetchRestaurant } from "@/lib/api";

export default function RestaurantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const restaurantId = params?.id as string;
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadRestaurant = async () => {
      try {
        setLoading(true);
        const data = await fetchRestaurant(restaurantId);
        setRestaurant(data);
      } catch (error) {
        console.error("Error fetching restaurant:", error);
        router.push("/home");
      } finally {
        setLoading(false);
      }
    };

    if (restaurantId) {
      loadRestaurant();
    }
  }, [restaurantId, router]);

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

  // Navigation handler that works with Next.js router
  const handleNavigate = (screen: Screen) => {
    switch (screen) {
      case "home":
        router.push("/home");
        break;
      case "room":
        router.push("/room");
        break;
      case "voting":
        router.push(`/voting/${restaurantId}`);
        break;
      case "rating":
        // Handle rating navigation if needed
        break;
      default:
        router.push("/home");
    }
  };

  // Check if user is in group mode (you can implement this based on your app state)
  const isGroupMode = false; // This could come from context or localStorage

  return (
    <RestaurantDetail
      restaurant={restaurant}
      onNavigate={handleNavigate}
      isGroupMode={isGroupMode}
    />
  );
}

