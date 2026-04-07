"use client";
import React, { useState, useEffect } from 'react';
import { ArrowLeft, MapPin, Clock, DollarSign, Star, Phone, Share2, Heart, Navigation, TrendingUp, Users } from 'lucide-react';
import { Screen, Restaurant } from '../../app/page';
import Image from "next/image";
import RestaurantMap from './RestaurantMap';
import { createRoom, addRestaurantToRoom, addMenuItemToRoom, fetchRestaurantMenu, fetchRoom } from '@/lib/api';
import { getParticipantId } from '@/lib/participant';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { formatPrice, formatPriceRange } from '@/lib/format';

interface RestaurantDetailProps {
  restaurant: Restaurant;
  onNavigate: (screen: Screen) => void;
  isGroupMode: boolean;
}

export default function RestaurantDetail({ restaurant, onNavigate, isGroupMode }: RestaurantDetailProps) {
  const [activeTab, setActiveTab] = useState<'menu' | 'reviews' | 'info'>('menu');
  const [isFavorite, setIsFavorite] = useState(false);
  const [currentRoomId, setCurrentRoomId] = useState<string | null>(null);
  const [addingToRoom, setAddingToRoom] = useState(false);
  const [menuItems, setMenuItems] = useState<Array<{ id: number; name: string; price: number }>>([]);
  const [loadingMenu, setLoadingMenu] = useState(false);
  const [addingMenuItemId, setAddingMenuItemId] = useState<number | null>(null);
  const [roomMenuItems, setRoomMenuItems] = useState<Set<number>>(new Set());
  const router = useRouter();

  // Load current room ID from localStorage and fetch room menu items
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedRoomId = localStorage.getItem('current_room_id');
      if (storedRoomId) {
        // Verify room still exists and is open, then fetch menu items
        fetchRoom(storedRoomId)
          .then(room => {
            if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
              setCurrentRoomId(storedRoomId);
              // Get menu item IDs that are already in the room
              const menuItemIds = new Set(room.menuItems.map(item => item.menuItemId));
              setRoomMenuItems(menuItemIds);
            } else {
              localStorage.removeItem('current_room_id');
              setCurrentRoomId(null);
              setRoomMenuItems(new Set());
            }
          })
          .catch(() => {
            localStorage.removeItem('current_room_id');
            setCurrentRoomId(null);
            setRoomMenuItems(new Set());
          });
      } else {
        setCurrentRoomId(null);
        setRoomMenuItems(new Set());
      }
    }
  }, []);

  // Refresh room menu items when menu items are loaded or when adding
  useEffect(() => {
    if (currentRoomId && menuItems.length > 0) {
      fetchRoom(currentRoomId)
        .then(room => {
          if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
            const menuItemIds = new Set(room.menuItems.map(item => item.menuItemId));
            setRoomMenuItems(menuItemIds);
          }
        })
        .catch(() => {
          // Room might have been closed
        });
    }
  }, [currentRoomId, menuItems.length, addingMenuItemId]);

  // Load menu items when menu tab is active
  useEffect(() => {
    if (activeTab === 'menu' && menuItems.length === 0) {
      const loadMenuItems = async () => {
        try {
          setLoadingMenu(true);
          const items = await fetchRestaurantMenu(restaurant.id);
          setMenuItems(items);
        } catch (error) {
          console.error('Error fetching menu items:', error);
        } finally {
          setLoadingMenu(false);
        }
      };
      loadMenuItems();
    }
  }, [activeTab, restaurant.id, menuItems.length]);

  const handleOrderNow = async () => {
    if (isGroupMode) {
      // Add to group order
      await handleAddToGroupOrder();
    } else {
      // Regular order flow (if needed)
      console.log("Order now for", restaurant.name);
    }
  };

  const handleAddToGroupOrder = async () => {
    try {
      setAddingToRoom(true);
      const participantId = getParticipantId();

      // Check if we have a current room, otherwise create one
      let roomId = currentRoomId;

      if (!roomId) {
        // Get from localStorage or create new
        const storedRoomId = typeof window !== 'undefined' ? localStorage.getItem('current_room_id') : null;

        if (storedRoomId) {
          // Check if room still exists and is open
          try {
            const room = await fetchRoom(storedRoomId);
            if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
              roomId = storedRoomId;
            }
          } catch {
            // Room doesn't exist, create new
            roomId = null;
          }
        }

        if (!roomId) {
          // Create new room
          const room = await createRoom(undefined, participantId);
          roomId = room.id;
          if (typeof window !== 'undefined') {
            localStorage.setItem('current_room_id', roomId);
          }
          setCurrentRoomId(roomId);
        }
      }

      // Add restaurant to room (adds "Anything" menu item)
      await addRestaurantToRoom(roomId, restaurant.id);

      // Navigate to voting page
      router.push(`/voting/${roomId}`);
    } catch (error) {
      console.error('Error adding to group order:', error);
      toast.error('Failed to add to group order. Please try again.');
    } finally {
      setAddingToRoom(false);
    }
  };

  const handleAddMenuItemToRoom = async (menuItemId: number) => {
    try {
      setAddingMenuItemId(menuItemId);
      const participantId = getParticipantId();

      // Check if we have a current room, otherwise create one
      let roomId = currentRoomId;

      if (!roomId) {
        // Get from localStorage or create new
        const storedRoomId = typeof window !== 'undefined' ? localStorage.getItem('current_room_id') : null;

        if (storedRoomId) {
          // Check if room still exists and is open
          try {
            const room = await fetchRoom(storedRoomId);
            if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
              roomId = storedRoomId;
            }
          } catch {
            // Room doesn't exist, create new
            roomId = null;
          }
        }

        if (!roomId) {
          // Create new room
          const room = await createRoom(undefined, participantId);
          roomId = room.id;
          if (typeof window !== 'undefined') {
            localStorage.setItem('current_room_id', roomId);
          }
          setCurrentRoomId(roomId);
        }
      }

      // Add specific menu item to room
      await addMenuItemToRoom(roomId, menuItemId);

      // Update room menu items list
      setRoomMenuItems(prev => new Set([...prev, menuItemId]));

      // Show success message
      toast.success('Menu item added to group order!');
    } catch (error) {
      console.error('Error adding menu item to room:', error);
      toast.error('Failed to add menu item to group order. Please try again.');
    } finally {
      setAddingMenuItemId(null);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header Image */}
      <div className="relative h-80 overflow-hidden">
        <img
          src={restaurant.image || '/images/default.png'}
          alt={restaurant.name}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>

        {/* Back Button */}
        <button
          onClick={() => onNavigate('home')}
          className="absolute top-4 left-4 w-10 h-10 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-white transition-all shadow-lg"
        >
          <ArrowLeft className="w-5 h-5 text-neutral-900" />
        </button>

        {/* Action Buttons */}
        <div className="absolute top-4 right-4 flex gap-2">
          <button
            onClick={() => setIsFavorite(!isFavorite)}
            className="w-10 h-10 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-white transition-all shadow-lg"
          >
            <Heart className={`w-5 h-5 ${isFavorite ? 'fill-red-500 text-red-500' : 'text-neutral-900'}`} />
          </button>
          <button className="w-10 h-10 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-white transition-all shadow-lg">
            <Share2 className="w-5 h-5 text-neutral-900" />
          </button>
        </div>

        {/* Restaurant Title */}
        <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
          <h1 className="mb-2">{restaurant.name}</h1>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
              <span>{restaurant.rating}</span>
              <span className="text-white/70 text-sm">({restaurant.reviews} reviews)</span>
            </div>
            <span className="text-white/90">{restaurant.cuisine}</span>
            <span className="text-white/90">{formatPriceRange(restaurant.priceRange)}</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 -mt-6 relative z-10">
        {/* Quick Info Cards */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="bg-white rounded-2xl p-4 shadow-sm text-center">
            <MapPin className="w-5 h-5 text-primary-orange mx-auto mb-1" />
            <p className="text-sm text-neutral-600">{restaurant.distance}</p>
            <p className="text-xs text-neutral-400">Distance</p>
          </div>
          <div className="bg-white rounded-2xl p-4 shadow-sm text-center">
            <Clock className="w-5 h-5 text-primary-green mx-auto mb-1" />
            <p className="text-sm text-neutral-600">25-30 min</p>
            <p className="text-xs text-neutral-400">Delivery</p>
          </div>
          <div className="bg-white rounded-2xl p-4 shadow-sm text-center">
            <TrendingUp className="w-5 h-5 text-primary-orange mx-auto mb-1" />
            <p className="text-sm text-neutral-600">{restaurant.pickCount}</p>
            <p className="text-xs text-neutral-400">Team Picks</p>
          </div>
        </div>

        {/* Contact & Location */}
        <div className="bg-white rounded-2xl p-6 shadow-sm mb-4">
          <h4 className="mb-4">Location & Contact</h4>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <MapPin className="w-5 h-5 text-neutral-400 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm">{restaurant.address}</p>
                <button
                  onClick={() => {
                    if (restaurant.latitude && restaurant.longitude) {
                      window.open(
                        `https://www.google.com/maps/dir/?api=1&origin=10.80108113092826,106.65039339473645&destination=${restaurant.latitude},${restaurant.longitude}`,
                        '_blank'
                      );
                    }
                  }}
                  className="text-primary-orange text-sm mt-1 flex items-center gap-1 hover:underline"
                >
                  <Navigation className="w-3 h-3" />
                  Get Directions
                </button>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-neutral-400" />
              <p className="text-sm">{restaurant.hours}</p>
            </div>
            <div className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-neutral-400" />
              <a href="tel:+1234567890" className="text-sm text-primary-orange hover:underline">
                (704) 555-0123
              </a>
            </div>
          </div>

          {/* Map */}
          {restaurant.latitude && restaurant.longitude && (
            <div className="mt-4">
              <RestaurantMap
                latitude={restaurant.latitude}
                longitude={restaurant.longitude}
                restaurantName={restaurant.name}
                address={restaurant.address}
              />
            </div>
          )}
        </div>

        {/* Description */}
        <div className="bg-white rounded-2xl p-6 shadow-sm mb-4">
          <h4 className="mb-3">About</h4>
          <p className="text-sm text-neutral-700 leading-relaxed">
            {restaurant.description}
          </p>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-t-2xl shadow-sm">
          <div className="flex border-b border-neutral-200">
            <button
              onClick={() => setActiveTab('menu')}
              className={`flex-1 py-4 text-sm transition-colors ${activeTab === 'menu'
                ? 'border-b-2 border-primary-orange text-primary-orange'
                : 'text-neutral-600'
                }`}
            >
              Menu
            </button>
            <button
              onClick={() => setActiveTab('reviews')}
              className={`flex-1 py-4 text-sm transition-colors ${activeTab === 'reviews'
                ? 'border-b-2 border-primary-orange text-primary-orange'
                : 'text-neutral-600'
                }`}
            >
              Reviews
            </button>
            <button
              onClick={() => setActiveTab('info')}
              className={`flex-1 py-4 text-sm transition-colors ${activeTab === 'info'
                ? 'border-b-2 border-primary-orange text-primary-orange'
                : 'text-neutral-600'
                }`}
            >
              Info
            </button>
          </div>

          <div className="p-6">
            {activeTab === 'menu' && (
              <div className="space-y-3">
                <h5 className="mb-4">Menu Items</h5>
                {loadingMenu ? (
                  <div className="text-center py-8 text-neutral-500">Loading menu...</div>
                ) : menuItems.length === 0 ? (
                  <div className="text-center py-8 text-neutral-500">No menu items available</div>
                ) : (
                  menuItems.map((item) => {
                    const isInRoom = roomMenuItems.has(item.id);
                    return (
                      <div key={item.id} className="flex items-center justify-between py-3 border-b border-neutral-100 last:border-0">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{item.name}</p>
                            {isInRoom && (
                              <span className="px-2 py-0.5 bg-primary-green/10 text-primary-green text-xs rounded-full">
                                In Group
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-neutral-500 mt-1">
                            {item.name === 'Anything' ? 'Default option' : 'Available'}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          {item.name !== 'Anything' && (
                            <p className="text-primary-orange font-medium">{formatPrice(item.price)}</p>
                          )}
                          <button
                            onClick={() => handleAddMenuItemToRoom(item.id)}
                            disabled={addingMenuItemId === item.id || isInRoom}
                            className={`px-4 py-2 rounded-full text-sm transition-all flex items-center gap-2 ${addingMenuItemId === item.id || isInRoom
                              ? 'bg-neutral-100 text-neutral-400 cursor-not-allowed'
                              : 'bg-primary-orange text-white hover:bg-primary-orange/90'
                              }`}
                          >
                            {addingMenuItemId === item.id ? (
                              <>
                                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                                <span>Adding...</span>
                              </>
                            ) : isInRoom ? (
                              <>
                                <Users className="w-4 h-4" />
                                <span>Added</span>
                              </>
                            ) : (
                              <>
                                <Users className="w-4 h-4" />
                                <span>Add to Group</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {activeTab === 'reviews' && (
              <div className="space-y-4">
                <div className="bg-neutral-50 rounded-xl p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-primary-orange rounded-full flex items-center justify-center text-white">
                      JS
                    </div>
                    <div>
                      <p className="text-sm">John Smith</p>
                      <div className="flex items-center gap-1">
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                      </div>
                    </div>
                    <span className="ml-auto text-xs text-neutral-500">2 days ago</span>
                  </div>
                  <p className="text-sm text-neutral-700">
                    Amazing food and great service! The portions are generous and everything tastes fresh. Definitely coming back!
                  </p>
                </div>

                <div className="bg-neutral-50 rounded-xl p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-primary-green rounded-full flex items-center justify-center text-white">
                      MJ
                    </div>
                    <div>
                      <p className="text-sm">Mary Johnson</p>
                      <div className="flex items-center gap-1">
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                        <Star className="w-3 h-3 text-neutral-300" />
                      </div>
                    </div>
                    <span className="ml-auto text-xs text-neutral-500">1 week ago</span>
                  </div>
                  <p className="text-sm text-neutral-700">
                    Good quality food at reasonable prices. Perfect for team lunches!
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'info' && (
              <div className="space-y-4">
                <div>
                  <h5 className="mb-2">Cuisine Type</h5>
                  <p className="text-sm text-neutral-700">{restaurant.cuisine}</p>
                </div>
                <div>
                  <h5 className="mb-2">Price Range</h5>
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-primary-green" />
                    <p className="text-sm text-neutral-700">
                      {formatPriceRange(restaurant.priceRange)} • Average ${15}-${25} per person
                    </p>
                  </div>
                </div>
                <div>
                  <h5 className="mb-2">Payment Methods</h5>
                  <p className="text-sm text-neutral-700">Cash, Credit Cards, Mobile Payment</p>
                </div>
                <div>
                  <h5 className="mb-2">Amenities</h5>
                  <div className="flex flex-wrap gap-2 mt-2">
                    <span className="px-3 py-1 bg-neutral-100 rounded-full text-xs">Dine-in</span>
                    <span className="px-3 py-1 bg-neutral-100 rounded-full text-xs">Takeout</span>
                    <span className="px-3 py-1 bg-neutral-100 rounded-full text-xs">Delivery</span>
                    <span className="px-3 py-1 bg-neutral-100 rounded-full text-xs">WiFi</span>
                    <span className="px-3 py-1 bg-neutral-100 rounded-full text-xs">Parking</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="sticky bottom-0 bg-white border-t border-neutral-200 p-4 rounded-b-2xl shadow-lg mb-6">
          <button
            onClick={handleAddToGroupOrder}
            disabled={addingToRoom}
            className="w-full bg-gradient-to-r from-primary-orange to-primary-green text-white py-4 rounded-full hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {addingToRoom ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Adding to Group Order...</span>
              </>
            ) : (
              <>
                <Users className="w-5 h-5" />
                <span>Add to Group Order</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}
