"use client";
import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { Restaurant } from "@/app/page";
import { useRouter } from "next/navigation";
import { formatPriceRange } from '@/lib/format';

interface AllRestaurantsMapProps {
  restaurants: Restaurant[];
  onRestaurantClick?: (restaurant: Restaurant) => void;
}

export default function AllRestaurantsMap({
  restaurants,
  onRestaurantClick,
}: AllRestaurantsMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markers = useRef<mapboxgl.Marker[]>([]);
  const router = useRouter();

  useEffect(() => {
    if (!mapContainer.current) return;

    // Get Mapbox token from environment variable
    const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;

    if (!mapboxToken) {
      console.warn("Mapbox access token not found. Please set NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN in your .env.local file");
      return;
    }

    // Initialize map only once
    if (!map.current) {
      mapboxgl.accessToken = mapboxToken;

      // Calculate center from all restaurants
      const restaurantsWithCoords = restaurants.filter(
        (r) => r.latitude && r.longitude
      );

      if (restaurantsWithCoords.length === 0) {
        return;
      }

      // Calculate bounds
      const lats = restaurantsWithCoords.map((r) => r.latitude!);
      const lngs = restaurantsWithCoords.map((r) => r.longitude!);
      const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2;
      const centerLng = (Math.min(...lngs) + Math.max(...lngs)) / 2;

      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: "mapbox://styles/mapbox/streets-v12",
        center: [centerLng, centerLat],
        zoom: 13,
      });

      // Fit bounds to show all restaurants
      if (restaurantsWithCoords.length > 1) {
        const bounds = new mapboxgl.LngLatBounds();
        restaurantsWithCoords.forEach((r) => {
          bounds.extend([r.longitude!, r.latitude!]);
        });
        map.current.fitBounds(bounds, {
          padding: { top: 50, bottom: 50, left: 50, right: 50 },
          maxZoom: 15,
        });
      }
    }

    // Clear existing markers
    markers.current.forEach((marker) => marker.remove());
    markers.current = [];

    // Add markers for all restaurants
    restaurants
      .filter((r) => r.latitude && r.longitude)
      .forEach((restaurant) => {
        const el = document.createElement("div");
        el.className = "marker";
        el.style.width = "32px";
        el.style.height = "32px";
        el.style.borderRadius = "50%";
        el.style.backgroundColor = "#f97316"; // primary-orange
        el.style.border = "3px solid white";
        el.style.boxShadow = "0 2px 4px rgba(0,0,0,0.3)";
        el.style.cursor = "pointer";

        const formattedPriceRange = formatPriceRange(restaurant.priceRange);
        const popup = new mapboxgl.Popup({ offset: 25, closeOnClick: false, closeButton: false }).setHTML(
          `<div class="p-3 min-w-[200px]">
            <h3 class="font-semibold text-sm mb-1">${restaurant.name}</h3>
            <p class="text-xs text-neutral-600 mb-2">${restaurant.cuisine} • ${formattedPriceRange}</p>
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xs">⭐ ${restaurant.rating}</span>
              <span class="text-xs text-neutral-500">•</span>
              <span class="text-xs text-neutral-500">${restaurant.distance}</span>
            </div>
            <p class="text-xs text-neutral-600">${restaurant.address}</p>
            <button 
              class="mt-2 w-full bg-primary-orange text-white text-xs py-1.5 px-3 rounded-lg hover:bg-primary-orange-dark transition-colors"
              onclick="window.location.href='/restaurant/${restaurant.id}'"
            >
              View Details
            </button>
          </div>`
        );

        const marker = new mapboxgl.Marker(el)
          .setLngLat([restaurant.longitude!, restaurant.latitude!])
          .setPopup(popup)
          .addTo(map.current!);

        // Add hover handlers to show/hide popup
        el.addEventListener("mouseenter", () => {
          if (map.current) {
            const popup = marker.getPopup();
            if (popup) {
              popup.addTo(map.current);
            }
          }
        });

        el.addEventListener("mouseleave", () => {
          const popup = marker.getPopup();
          if (popup) {
            popup.remove();
          }
        });

        // Add click handler
        el.addEventListener("click", () => {
          if (onRestaurantClick) {
            onRestaurantClick(restaurant);
          } else {
            router.push(`/restaurant/${restaurant.id}`);
          }
        });

        markers.current.push(marker);
      });

    // Cleanup
    return () => {
      markers.current.forEach((marker) => marker.remove());
      markers.current = [];
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [restaurants, onRestaurantClick, router]);

  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;

  if (!mapboxToken) {
    return (
      <div className="w-full h-[600px] bg-neutral-100 rounded-2xl flex items-center justify-center border border-neutral-200">
        <div className="text-center p-4">
          <p className="text-sm text-neutral-600 mb-2">
            Mapbox token not configured
          </p>
          <p className="text-xs text-neutral-500">
            Please set NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN in .env.local
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-[600px] rounded-2xl overflow-hidden border border-neutral-200">
      <div ref={mapContainer} className="w-full h-full" />
    </div>
  );
}

