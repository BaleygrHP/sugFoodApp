"use client";
import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

interface RestaurantMapProps {
  latitude: number;
  longitude: number;
  restaurantName: string;
  address: string;
}

export default function RestaurantMap({
  latitude,
  longitude,
  restaurantName,
  address,
}: RestaurantMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const marker = useRef<mapboxgl.Marker | null>(null);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Get Mapbox token from environment variable
    const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;

    if (!mapboxToken) {
      console.warn("Mapbox access token not found. Please set NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN in your .env.local file");
      return;
    }

    mapboxgl.accessToken = mapboxToken;

    // Initialize map
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [longitude, latitude],
      zoom: 15,
    });

    // Add marker
    marker.current = new mapboxgl.Marker({
      color: "#f97316", // primary-orange color
    })
      .setLngLat([longitude, latitude])
      .setPopup(
        new mapboxgl.Popup({ offset: 25 }).setHTML(
          `<div class="p-2">
            <h3 class="font-semibold text-sm">${restaurantName}</h3>
            <p class="text-xs text-neutral-600">${address}</p>
          </div>`
        )
      )
      .addTo(map.current);

    // Cleanup
    return () => {
      if (marker.current) {
        marker.current.remove();
        marker.current = null;
      }
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [latitude, longitude, restaurantName, address]);

  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;

  if (!mapboxToken) {
    return (
      <div className="w-full h-64 bg-neutral-100 rounded-xl flex items-center justify-center border border-neutral-200">
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
    <div className="w-full h-64 rounded-xl overflow-hidden border border-neutral-200">
      <div ref={mapContainer} className="w-full h-full" />
    </div>
  );
}

