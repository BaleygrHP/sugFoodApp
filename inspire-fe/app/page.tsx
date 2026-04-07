import { redirect } from "next/navigation";
export type Screen = 'login' | 'home' | 'room' | 'detail' | 'voting' | 'rating';


export interface MenuItem {
  name: string;
  price: number;
}

export interface Restaurant {
  id: string;
  name: string;
  cuisine: string;
  priceRange: string;
  rating: number;
  distance: string;
  hours: string;
  address: string;
  image: string;
  pickCount: number;
  description: string;
  menuItems: MenuItem[];
  reviews: number;
  latitude?: number;
  longitude?: number;
}

export interface VoteData {
  restaurantId: string;
  votes: number;
}


export default function Home() {
  redirect("/login");
}
