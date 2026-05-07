"use client";
import React, { useState, useEffect } from "react";
import {
  Search,
  Filter,
  MapPin,
  Users,
  User,
  Bot,
  Map,
  List,
  TrendingUp,
  Star,
  X,
  Send,
  SlidersHorizontal,
  DollarSign,
  Navigation2,
  Heart,
  History,
  Sparkles,
  Clock,
  ArrowRight,
  Plus,
} from "lucide-react";
import { Restaurant } from "../../app/page";
import { useRouter } from "next/navigation";
import AllRestaurantsMap from "./AllRestaurantsMap";
import {
  addRestaurantToShortlist,
  createRoom,
  fetchRestaurants,
  fetchRoom,
  fetchSpotlightRestaurant,
  requestAiChatSuggestions,
} from "@/lib/api";
import { toast } from 'sonner';
import AIMessageContent from './AIMessageContent';
import { formatPriceRange } from '@/lib/format';
import AddRestaurantForm from './AddRestaurantForm';

export default function HomeScreen() {
  const [viewMode, setViewMode] = useState<"list" | "map">("list");
  const [searchQuery, setSearchQuery] = useState("");
  const [showAI, setShowAI] = useState(false);
  const [aiMessage, setAiMessage] = useState("");
  const [aiMessages, setAiMessages] = useState<
    Array<{ role: "user" | "ai"; text: string; reason?: string }>
  >([
    {
      role: "ai",
      text: "👋 Hi! I can help you find the perfect meal. What are you craving today?",
    },
  ]);
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);
  const [spotlightRestaurant, setSpotlightRestaurant] = useState<Restaurant | null>(null);
  const [aiRecommendations, setAiRecommendations] = useState<Restaurant[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [currentRoomId, setCurrentRoomId] = useState<string | null>(null);
  const [addingToRoom, setAddingToRoom] = useState<string | null>(null);
  const [restaurantsInShortlist, setRestaurantsInShortlist] = useState<Set<string>>(new Set());
  const [filterCuisine, setFilterCuisine] = useState("all");
  const [vietnameseRegion, setVietnameseRegion] = useState("all");
  const [dishType, setDishType] = useState("all");
  const [priceRange, setPriceRange] = useState<string[]>(["$", "$$", "$$$"]);
  const [distanceRange, setDistanceRange] = useState(5);
  const [sortBy, setSortBy] = useState<"rating" | "price" | "distance">(
    "rating"
  );
  const [showFilters, setShowFilters] = useState(false);
  const [favorites, setFavorites] = useState<string[]>(["1", "6"]); // Mock favorite restaurant IDs
  const [showProfile, setShowProfile] = useState(false);
  const [showAddRestaurant, setShowAddRestaurant] = useState(false);
  const router = useRouter();

  const handleRestaurantAdded = async () => {
    // Refresh restaurants list
    try {
      const restaurantsData = await fetchRestaurants();
      setRestaurants(restaurantsData);
    } catch (error) {
      console.error('Error refreshing restaurants:', error);
    }
  };

  // Load current room ID from localStorage and fetch shortlisted restaurants.
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedRoomId = localStorage.getItem('current_room_id');
      if (storedRoomId) {
        fetchRoom(storedRoomId)
          .then(room => {
            if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
              setCurrentRoomId(storedRoomId);
              const restaurantIds = room.status === "open"
                ? new Set(
                    room.shortlistItems
                      .filter(item => item.menuItemName === 'Anything')
                      .map(item => item.restaurant.id)
                  )
                : new Set<string>();
              setRestaurantsInShortlist(restaurantIds);
            } else {
              localStorage.removeItem('current_room_id');
              setCurrentRoomId(null);
              setRestaurantsInShortlist(new Set());
            }
          })
          .catch(() => {
            localStorage.removeItem('current_room_id');
            setCurrentRoomId(null);
            setRestaurantsInShortlist(new Set());
          });
      } else {
        setRestaurantsInShortlist(new Set());
      }
    }
  }, []);

  // Refresh shortlisted restaurants when the room changes or after adding.
  useEffect(() => {
    if (currentRoomId) {
      fetchRoom(currentRoomId)
        .then(room => {
          if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
            const restaurantIds = room.status === "open"
              ? new Set(
                  room.shortlistItems
                    .filter(item => item.menuItemName === 'Anything')
                    .map(item => item.restaurant.id)
                )
              : new Set<string>();
            setRestaurantsInShortlist(restaurantIds);
          }
        })
        .catch(() => {
          // Room might have been closed
        });
    }
  }, [currentRoomId, addingToRoom]);

  // Fetch restaurants and spotlight restaurant from API (only once on mount)
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        // Fetch both in parallel
        const [restaurantsData, spotlightData] = await Promise.all([
          fetchRestaurants(),
          fetchSpotlightRestaurant().catch((error) => {
            console.error("Error fetching spotlight restaurant:", error);
            return null;
          }),
        ]);
        setRestaurants(restaurantsData);
        setSpotlightRestaurant(spotlightData);
      } catch (error) {
        console.error("Error fetching restaurants:", error);
        setRestaurants([]);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);


  const handleRestaurantClick = (restaurant: Restaurant) => {
    // onNavigate('detail', restaurant);
    router.push(`/restaurant/${restaurant.id}`);
  };

  const updateShortlistedRestaurants = (room: { id: string; shortlistItems: Array<{ menuItemName: string; restaurant: { id: string } }> }) => {
    const shortlistedRestaurantIds = new Set(
      room.shortlistItems
        .filter((item) => item.menuItemName === "Anything")
        .map((item) => item.restaurant.id),
    );

    setCurrentRoomId(room.id);
    setRestaurantsInShortlist(shortlistedRestaurantIds);

    if (typeof window !== "undefined") {
      localStorage.setItem("current_room_id", room.id);
    }
  };

  const getOrCreateOpenRoom = async () => {
    const candidateRoomIds = Array.from(
      new Set(
        [currentRoomId, typeof window !== "undefined" ? localStorage.getItem("current_room_id") : null].filter(Boolean),
      ),
    ) as string[];

    for (const roomId of candidateRoomIds) {
      try {
        const room = await fetchRoom(roomId);
        if (room.status === "open") {
          updateShortlistedRestaurants(room);
          return room;
        }
      } catch {
        // Ignore stale room ids and create a fresh room below.
      }
    }

    const room = await createRoom();
    updateShortlistedRestaurants(room);
    return room;
  };

  const handleAddRestaurantToShortlist = async (e: React.MouseEvent, restaurant: Restaurant) => {
    e.stopPropagation();

    try {
      setAddingToRoom(restaurant.id);
      const room = await getOrCreateOpenRoom();
      const updatedRoom = await addRestaurantToShortlist(room.id, restaurant.id);
      updateShortlistedRestaurants(updatedRoom);

      toast.success("Added to room shortlist. Ask the group for preferences when ready.");
      router.push(`/voting/${updatedRoom.id}`);
    } catch (error) {
      console.error("Error adding to room shortlist:", error);
      toast.error("Failed to add restaurant to the room shortlist. Please try again.");
    } finally {
      setAddingToRoom(null);
    }
  };

  const applyAiSuggestionResult = (matchedRestaurantIds: string[]) => {
    const recommendationIds = new Set(matchedRestaurantIds);
    setAiRecommendations(
      restaurants.filter((restaurant) => recommendationIds.has(restaurant.id)).slice(0, 5),
    );
  };

  const sendAiSuggestionRequest = async (message: string, keywords: string[] = []) => {
    const suggestion = await requestAiChatSuggestions(message, keywords);
    applyAiSuggestionResult(suggestion.matchedRestaurantIds);
    setAiMessages((prev) => [
      ...prev,
      {
        role: "ai",
        text: suggestion.reply,
        reason:
          suggestion.source === "fallback"
            ? "Using the Vietnamese fallback engine while the AI service is unavailable."
            : undefined,
      },
    ]);
  };

  const handleAISubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiMessage.trim()) return;

    const userMessage = aiMessage.trim();
    setAiMessages((prev) => [...prev, { role: "user", text: userMessage }]);
    setAiMessage("");
    setAiLoading(true);

    try {
      await sendAiSuggestionRequest(userMessage);
    } catch (error) {
      console.error("Error loading AI chat suggestions:", error);
      setAiRecommendations([]);
      setAiMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: "I could not load suggestions right now. Please try again in a moment.",
        },
      ]);
      toast.error("Failed to load AI suggestions.");
    } finally {
      setAiLoading(false);
    }
  };

  const handleSuggestionChip = async (chipLabel: string, keywords: string) => {
    setAiMessages((prev) => [...prev, { role: "user", text: chipLabel }]);
    setAiLoading(true);

    try {
      await sendAiSuggestionRequest(
        chipLabel,
        keywords
          .split(",")
          .map((keyword) => keyword.trim())
          .filter(Boolean),
      );
    } catch (error) {
      console.error("Error loading AI chip suggestions:", error);
      setAiRecommendations([]);
      setAiMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: "I could not load suggestions right now. Please try another prompt.",
        },
      ]);
      toast.error("Failed to load AI suggestions.");
    } finally {
      setAiLoading(false);
    }
  };

  const filteredRestaurants = restaurants.filter((restaurant) => {
    const matchesSearch =
      restaurant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      restaurant.cuisine.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCuisine =
      filterCuisine === "all" || restaurant.cuisine === filterCuisine;
    // Price range filter removed - no longer filtering by price
    return matchesSearch && matchesCuisine;
  });

  // Sort restaurants based on sortBy
  const sortedRestaurants = [...filteredRestaurants].sort((a, b) => {
    if (sortBy === "rating") {
      // Sort by rating (descending - highest first)
      return b.rating - a.rating;
    } else if (sortBy === "price") {
      // Sort by price range (ascending)
      // Helper function to convert price range to numeric value for comparison
      const getPriceValue = (priceRange: string): number => {
        // Handle numeric price ranges like "~50"
        const tildeMatch = priceRange.match(/^~(\d+)$/);
        if (tildeMatch) {
          return parseInt(tildeMatch[1], 10);
        }

        // Handle plain numbers like "50"
        const numberMatch = priceRange.match(/^(\d+)$/);
        if (numberMatch) {
          return parseInt(numberMatch[1], 10);
        }

        // Default: put unknown formats (like "$", "$$", "$$$") at the end
        return Infinity;
      };

      const priceA = getPriceValue(a.priceRange);
      const priceB = getPriceValue(b.priceRange);
      return priceA - priceB;
    } else if (sortBy === "distance") {
      // Sort by distance (ascending - closest first)
      // Parse distance string like "0.2 km" to number
      const parseDistance = (distanceStr: string): number => {
        const match = distanceStr.match(/(\d+\.?\d*)/);
        return match ? parseFloat(match[1]) : Infinity;
      };
      const distanceA = parseDistance(a.distance);
      const distanceB = parseDistance(b.distance);
      return distanceA - distanceB;
    }
    return 0;
  });

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <img src="./images/logo.png" className="w-20" />
              <div>
                <h3 className="text-primary-orange">CLT Eater</h3>
                <p className="text-xs text-neutral-500">CLV Company</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowAI(!showAI)}
                className="p-2 rounded-full hover:bg-neutral-100 transition-colors relative"
              >
                <Bot className="w-6 h-6 text-primary-green" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-primary-orange rounded-full"></span>
              </button>
              <div className="w-10 h-10 bg-neutral-200 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-neutral-600" />
              </div>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative mb-4">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
            <input
              type="text"
              placeholder="Search restaurants, cuisines..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-neutral-300 rounded-full focus:outline-none focus:ring-2 focus:ring-primary-orange focus:border-transparent"
            />
          </div>

          {/* Create room and AI food assistant buttons */}
          <div className="flex items-center gap-3 mb-4">
            {!currentRoomId && (
              <button
                onClick={() => router.push("/room")}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-orange to-primary-green text-white rounded-full hover:shadow-md transition-all font-medium"
              >
                <Users className="w-5 h-5" />
                <span>Create Decision Room</span>
              </button>
            )}
            <button
              onClick={() => setShowAI(!showAI)}
              className={`flex items-center gap-2 px-4 py-3 bg-white border border-primary-orange rounded-full hover:bg-primary-orange/5 transition-all ${!currentRoomId ? '' : 'ml-auto'}`}
            >
              <Bot className="w-4 h-4 text-primary-orange" />
              <span className="text-sm text-neutral-900 font-medium">AI Assistant</span>
              {showAI ? (
                <span className="text-xs text-neutral-400">▼</span>
              ) : (
                <span className="text-xs text-neutral-400">▶</span>
              )}
            </button>
          </div>
          {/* AI Assistant Panel - Inline Expanded */}
          {showAI && (
            <div className="relative mb-4">
              <div className="bg-white rounded-2xl shadow-lg border-2 border-primary-orange overflow-hidden">
                {/* Header */}
                <div className="bg-white border-b border-neutral-200 p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-orange/10 rounded-lg flex items-center justify-center">
                        <Bot className="w-5 h-5 text-primary-orange" />
                      </div>
                      <div>
                        <h5 className="text-neutral-900">AI Food Assistant</h5>
                        <p className="text-xs text-green-600">Online</p>
                      </div>
                    </div>
                    <button
                      onClick={() => setShowAI(false)}
                      className="text-neutral-400 hover:text-neutral-600 transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Suggestion Chips - Removed label, just chips */}
                <div className="p-4 border-b border-neutral-100 bg-neutral-50">
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() =>
                        handleSuggestionChip("😔 Feeling Sad", "sad")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      😔 Feeling Sad
                    </button>
                    <button
                      onClick={() =>
                        handleSuggestionChip("🥳 Just got paid", "paid")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      🥳 Just got paid
                    </button>
                    <button
                      onClick={() =>
                        handleSuggestionChip("🤯 Stressed out", "stress")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      🤯 Stressed out
                    </button>
                    <button
                      onClick={() =>
                        handleSuggestionChip("🌧️ It's raining", "rain")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      🌧️ It&apos;s raining
                    </button>
                    <button
                      onClick={() =>
                        handleSuggestionChip("🥗 Healthy Options", "health")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      🥗 Healthy Options
                    </button>
                    <button
                      onClick={() =>
                        handleSuggestionChip("💸 On a Budget", "budget")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      💸 On a Budget
                    </button>
                    <button
                      onClick={() =>
                        handleSuggestionChip("👩‍❤️‍👨 Date Night", "date")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      👩‍❤️‍👨 Date Night
                    </button>
                    <button
                      onClick={() =>
                        handleSuggestionChip("🍻 Group Gathering", "group")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      🍻 Group Gathering
                    </button>
                    <button
                      onClick={() =>
                        handleSuggestionChip("⚡ Quick Lunch", "quick")
                      }
                      className="px-3 py-1.5 bg-white text-neutral-700 rounded-full text-xs hover:bg-neutral-100 transition-colors border border-neutral-200 shadow-sm"
                    >
                      ⚡ Quick Lunch
                    </button>
                  </div>
                </div>

                {/* Chat Messages */}
                <div className="p-6 min-h-[400px] max-h-[500px] overflow-y-auto bg-white">
                  {aiMessages.map((message, index) => (
                    <div key={index} className="mb-4">
                      {message.role === "ai" ? (
                        <div className="flex gap-3">
                          <div className="w-8 h-8 bg-primary-orange/10 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Bot className="w-4 h-4 text-primary-orange" />
                          </div>
                          <div className="flex-1">
                            <div className="bg-neutral-100 rounded-2xl rounded-tl-none p-4">
                              <AIMessageContent text={message.text} restaurants={restaurants} />
                              {message.reason && (
                                <p className="text-xs text-neutral-600 mt-2 italic">
                                  💡 {message.reason}
                                </p>
                              )}
                            </div>
                            <p className="text-xs text-neutral-400 mt-1 ml-1">
                              {new Date().toLocaleTimeString("en-US", {
                                hour: "numeric",
                                minute: "2-digit",
                              })}
                            </p>

                            {/* Show recommendation cards after AI messages */}
                            {index === aiMessages.length - 1 &&
                              aiRecommendations.length > 0 && (
                                <div className="mt-3 space-y-2">
                                  {aiRecommendations.map((restaurant) => (
                                    <div
                                      key={restaurant.id}
                                      onClick={() => {
                                        handleRestaurantClick(restaurant);
                                        setShowAI(false);
                                      }}
                                      className="bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all cursor-pointer border border-neutral-200"
                                    >
                                      <div className="flex gap-3 p-3">
                                        <img src={restaurant.image || '/images/default.png'} alt={restaurant.name} className="w-20 h-20 rounded-lg object-cover" />
                                        <div className="flex-1 min-w-0">
                                          <h5 className="text-sm mb-1 truncate">
                                            {restaurant.name}
                                          </h5>
                                          <p className="text-xs text-neutral-600 mb-1">
                                            {restaurant.cuisine}
                                          </p>
                                          <div className="flex items-center gap-2 text-xs text-neutral-500">
                                            <span>⭐ {restaurant.rating}</span>
                                            <span>•</span>
                                            <span>{formatPriceRange(restaurant.priceRange)}</span>
                                            <span>•</span>
                                            <span>
                                              📍 {restaurant.distance}
                                            </span>
                                          </div>
                                        </div>
                                        <ArrowRight className="w-4 h-4 text-neutral-400 flex-shrink-0 self-center" />
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                          </div>
                        </div>
                      ) : (
                        <div className="flex justify-end">
                          <div className="bg-primary-orange text-white rounded-2xl rounded-tr-none p-3 max-w-[70%]">
                            <p className="text-sm">{message.text}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Loading indicator at the end */}
                  {aiLoading && aiMessages[aiMessages.length - 1]?.role === "user" && (
                    <div className="mb-4 flex gap-3">
                      <div className="w-8 h-8 bg-primary-orange/10 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-primary-orange animate-pulse" />
                      </div>
                      <div className="flex-1">
                        <div className="bg-neutral-100 rounded-2xl rounded-tl-none p-3">
                          <p className="text-sm text-neutral-500">Thinking...</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Input Form */}
                <form
                  onSubmit={handleAISubmit}
                  className="p-4 border-t border-neutral-200 bg-white"
                >
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Ask me anything about food..."
                      value={aiMessage}
                      onChange={(e) => setAiMessage(e.target.value)}
                      className="flex-1 px-4 py-3 bg-neutral-50 border border-neutral-200 rounded-full focus:outline-none focus:ring-2 focus:ring-primary-orange focus:bg-white text-sm"
                    />
                    <button
                      type="submit"
                      className="w-12 h-12 bg-primary-orange text-white rounded-full hover:bg-primary-orange/90 transition-colors flex items-center justify-center flex-shrink-0"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Filter & Sort Bar */}

        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Daily Spotlight Section */}
        {spotlightRestaurant && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-primary-orange" />
              <h4>Today&apos;s Spotlight</h4>
            </div>
            <div className="flex flex-col items-between justify-evenly bg-gradient-to-br from-primary-orange via-primary-green to-primary-orange p-6 rounded-2xl shadow-lg text-white">
              <div className="flex flex-row items-between justify-between gap-4 items-center">
                <div>
                  <div className="inline-block bg-white/20 px-3 py-1 rounded-full text-xs mb-2">
                    🏆 Top Pick Today ({spotlightRestaurant.pickCount} picks)
                  </div>
                  <h3 className="text-white mb-2">{spotlightRestaurant.name}</h3>
                  <p className="text-white/90 mb-3 text-sm">
                    {spotlightRestaurant.description || "Local favorite with authentic flavors. Perfect for a quick, delicious meal!"}
                  </p>
                  <div className="flex items-center gap-4 mb-3">
                    <span className="text-sm">⭐ {spotlightRestaurant.rating} Rating</span>
                    <span className="text-sm">📍 {spotlightRestaurant.distance}</span>
                    <span className="text-sm">💰 {formatPriceRange(spotlightRestaurant.priceRange)}</span>
                  </div>
                  <button
                    onClick={() => handleRestaurantClick(spotlightRestaurant)}
                    className="bg-white text-primary-orange px-6 py-2 rounded-full hover:shadow-lg transition-all inline-flex items-center gap-2"
                  >
                    <span>View Details</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
                <div className="relative h-48 md:h-auto">
                  <img
                    src={spotlightRestaurant.image || "/images/default.png"}
                    alt={spotlightRestaurant.name}
                    className="w-120 h-75 object-cover rounded-xl"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Based on What You Ate Section */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <History className="w-5 h-5 text-primary-green" />
            <h4>Based on What You Ate</h4>
            <span className="text-xs text-neutral-500">
              (You frequently ordered Asian & Mexican)
            </span>
          </div>
          <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide">
            {restaurants
              .filter(
                (r) => r.cuisine === "Asian Fusion" || r.cuisine === "Mexican"
              )
              .map((restaurant) => (
                <div
                  key={restaurant.id}
                  onClick={() => handleRestaurantClick(restaurant)}
                  className="flex-shrink-0 w-64 bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-lg transition-all cursor-pointer"
                >
                  <div className="relative h-40">
                    <img
                      src={restaurant.image || '/images/default.png'}
                      alt={restaurant.name}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 right-2 bg-white px-2 py-1 rounded-full text-xs">
                      ⭐ {restaurant.rating}
                    </div>
                    <div className="absolute top-2 left-2 bg-primary-green text-white px-2 py-1 rounded-full text-xs">
                      Recommended
                    </div>
                  </div>
                  <div className="p-3">
                    <h5 className="mb-1">{restaurant.name}</h5>
                    <p className="text-xs text-neutral-600 mb-2">
                      {restaurant.cuisine} • {formatPriceRange(restaurant.priceRange)} •{" "}
                      {restaurant.distance}
                    </p>
                    <p className="text-xs text-neutral-500 italic">
                      &quot;Because you loved similar places!&quot;
                    </p>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Your Favorites Section */}
        {favorites.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <Heart className="w-5 h-5 text-red-500 fill-red-500" />
              <h4>Your Favorites</h4>
            </div>
            <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-hide">
              {restaurants
                .filter((r) => favorites.includes(r.id))
                .map((restaurant) => (
                  <div
                    key={restaurant.id}
                    onClick={() => handleRestaurantClick(restaurant)}
                    className="flex-shrink-0 w-64 bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-lg transition-all cursor-pointer border-2 border-red-100"
                  >
                    <div className="relative h-40">
                      <img
                        src={restaurant.image || '/images/default.png'}
                        alt={restaurant.name}

                        className="w-full h-full object-cover"
                      />
                      <div className="absolute top-2 right-2 bg-white px-2 py-1 rounded-full text-xs">
                        ⭐ {restaurant.rating}
                      </div>
                      <div className="absolute top-2 left-2 bg-red-500 text-white p-2 rounded-full">
                        <Heart className="w-4 h-4 fill-white" />
                      </div>
                    </div>
                    <div className="p-3">
                      <h5 className="mb-1">{restaurant.name}</h5>
                      <p className="text-xs text-neutral-600 mb-2">
                        {restaurant.cuisine} • {formatPriceRange(restaurant.priceRange)} •{" "}
                        {restaurant.distance}
                      </p>
                      <div className="flex items-center gap-2">
                        <Clock className="w-3 h-3 text-neutral-400" />
                        <span className="text-xs text-neutral-500">
                          Last visited 3 days ago
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Pending Reviews Banner */}
        <div className="bg-amber-50 border-2 border-amber-200 rounded-2xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
              <Star className="w-5 h-5 text-amber-600" />
            </div>
            <div className="flex-1">
              <h5 className="text-amber-900 mb-1">Pending Reviews</h5>
              <p className="text-sm text-amber-700 mb-3">
                You have 2 meals to rate! Help others find great food.
              </p>
              <div className="flex gap-2">
                <button className="px-4 py-2 bg-amber-500 text-white rounded-full text-sm hover:bg-amber-600 transition-colors">
                  Rate Golden Dragon
                </button>
                <button className="px-4 py-2 bg-amber-500 text-white rounded-full text-sm hover:bg-amber-600 transition-colors">
                  Rate Taco Street
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* All Restaurants Header */}
        <div className="flex items-center justify-between mb-4">
          <h4>All Restaurants</h4>
          <button
            onClick={() => setShowAddRestaurant(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-orange text-white rounded-full hover:bg-primary-orange/90 transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            Add Restaurant
          </button>
        </div>

        {/* Sort Buttons */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-neutral-600 mr-2">Sort by:</span>
            <button
              onClick={() => setSortBy("rating")}
              className={`px-3 py-1.5 rounded-full text-sm transition-all ${sortBy === "rating"
                ? "bg-primary-orange text-white"
                : "bg-white text-neutral-700 hover:bg-neutral-200"
                }`}
            >
              <div className="flex items-center gap-1">
                <Star className="w-3 h-3" />
                Rating
              </div>
            </button>
            <button
              onClick={() => setSortBy("price")}
              className={`px-3 py-1.5 rounded-full text-sm transition-all ${sortBy === "price"
                ? "bg-primary-orange text-white"
                : "bg-white text-neutral-700 hover:bg-neutral-200"
                }`}
            >
              <div className="flex items-center gap-1">
                <DollarSign className="w-3 h-3" />
                Price
              </div>
            </button>
            <button
              onClick={() => setSortBy("distance")}
              className={`px-3 py-1.5 rounded-full text-sm transition-all ${sortBy === "distance"
                ? "bg-primary-orange text-white"
                : "bg-white text-neutral-700 hover:bg-neutral-200"
                }`}
            >
              <div className="flex items-center gap-1">
                <Navigation2 className="w-3 h-3" />
                Distance
              </div>
            </button>
          </div>
          <div className="flex gap-2">
            <div className="flex bg-neutral-100 rounded-full p-1">
              <button
                onClick={() => setViewMode("list")}
                className={`p-2 rounded-full transition-all ${viewMode === "list" ? "bg-white shadow-sm" : ""
                  }`}
              >
                <List className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode("map")}
                className={`p-2 rounded-full transition-all ${viewMode === "map" ? "bg-white shadow-sm" : ""
                  }`}
              >
                <Map className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Advanced Filters - Temporarily commented out */}
        {false && showFilters && (
          <div className="bg-white rounded-xl p-4 space-y-4">
            {/* Cuisine Filter */}
            <div>
              <label className="block text-sm text-neutral-700 mb-2">
                Cuisine Type
              </label>
              <select
                value={filterCuisine}
                onChange={(e) => setFilterCuisine(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-orange"
              >
                <option value="all">All Cuisines</option>
                <option value="Korean">Korean</option>
                <option value="Vietnamese">Vietnamese</option>
                <option value="Thai">Thai</option>
                <option value="Japanese">Japanese</option>
                <option value="Indian">Indian</option>
                <option value="Western">Western</option>
                <option value="Street Food">Street Food</option>
                <option value="Italian">Italian</option>
                <option value="Mexican">Mexican</option>
                <option value="American">American</option>
              </select>

              {/* Vietnamese Region Sub-filter */}
              {filterCuisine === "Vietnamese" && (
                <div className="mt-2">
                  <label className="block text-xs text-neutral-600 mb-2">
                    Vietnamese Region
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setVietnameseRegion("all")}
                      className={`px-3 py-1 rounded-full text-xs transition-all ${vietnameseRegion === "all"
                        ? "bg-primary-green text-white"
                        : "bg-neutral-100 text-neutral-700"
                        }`}
                    >
                      All
                    </button>
                    <button
                      onClick={() => setVietnameseRegion("north")}
                      className={`px-3 py-1 rounded-full text-xs transition-all ${vietnameseRegion === "north"
                        ? "bg-primary-green text-white"
                        : "bg-neutral-100 text-neutral-700"
                        }`}
                    >
                      North
                    </button>
                    <button
                      onClick={() => setVietnameseRegion("middle")}
                      className={`px-3 py-1 rounded-full text-xs transition-all ${vietnameseRegion === "middle"
                        ? "bg-primary-green text-white"
                        : "bg-neutral-100 text-neutral-700"
                        }`}
                    >
                      Middle
                    </button>
                    <button
                      onClick={() => setVietnameseRegion("south")}
                      className={`px-3 py-1 rounded-full text-xs transition-all ${vietnameseRegion === "south"
                        ? "bg-primary-green text-white"
                        : "bg-neutral-100 text-neutral-700"
                        }`}
                    >
                      South
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Dish Type Filter */}
            <div>
              <label className="block text-sm text-neutral-700 mb-2">
                Dish Type
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setDishType("all")}
                  className={`px-4 py-2 rounded-lg text-sm transition-all ${dishType === "all"
                    ? "bg-primary-orange text-white"
                    : "bg-neutral-100 text-neutral-700"
                    }`}
                >
                  All
                </button>
                <button
                  onClick={() => setDishType("dry")}
                  className={`px-4 py-2 rounded-lg text-sm transition-all ${dishType === "dry"
                    ? "bg-primary-orange text-white"
                    : "bg-neutral-100 text-neutral-700"
                    }`}
                >
                  Dry Dishes
                </button>
                <button
                  onClick={() => setDishType("soup")}
                  className={`px-4 py-2 rounded-lg text-sm transition-all ${dishType === "soup"
                    ? "bg-primary-orange text-white"
                    : "bg-neutral-100 text-neutral-700"
                    }`}
                >
                  Soup Dishes
                </button>
              </div>
            </div>

            {/* Distance Slider */}
            <div>
              <label className="block text-sm text-neutral-700 mb-2">
                Distance:{" "}
                {distanceRange >= 5 ? "5+ km" : `${distanceRange} km`}
              </label>
              <input
                type="range"
                min="1"
                max="5"
                step="1"
                value={distanceRange}
                onChange={(e) => setDistanceRange(Number(e.target.value))}
                className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer accent-primary-orange"
              />
              <div className="flex justify-between text-xs text-neutral-500 mt-1">
                <span>1 km</span>
                <span>2 km</span>
                <span>3 km</span>
                <span>4 km</span>
                <span>5+ km</span>
              </div>
            </div>

            {/* Clear Filters Button */}
            <button
              onClick={() => {
                setFilterCuisine("all");
                setVietnameseRegion("all");
                setDishType("all");
                setPriceRange(["$", "$$", "$$$"]);
                setDistanceRange(5);
              }}
              className="w-full px-4 py-2 bg-neutral-100 text-neutral-700 rounded-lg text-sm hover:bg-neutral-200 transition-all"
            >
              Clear All Filters
            </button>
          </div>
        )}

        {/* Stats Bar */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-primary-orange" />
              <span className="text-xs text-neutral-500">Trending</span>
            </div>
            <p className="text-sm">Street Eats</p>
          </div>
          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <Star className="w-4 h-4 text-primary-green" />
              <span className="text-xs text-neutral-500">Top Rated</span>
            </div>
            <p className="text-sm">Taco Street</p>
          </div>
          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <MapPin className="w-4 h-4 text-neutral-600" />
              <span className="text-xs text-neutral-500">Closest</span>
            </div>
            <p className="text-sm">Street Eats</p>
          </div>
        </div>

        {/* Restaurant List */}
        {viewMode === "list" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {loading ? (
              <div className="col-span-full text-center py-12">
                <div className="text-lg text-neutral-500">Loading restaurants...</div>
              </div>
            ) : sortedRestaurants.length === 0 ? (
              <div className="col-span-full text-center py-12">
                <div className="text-lg text-neutral-500">No restaurants found</div>
              </div>
            ) : (
              sortedRestaurants.map((restaurant) => (
                <div
                  key={restaurant.id}
                  onClick={() => handleRestaurantClick(restaurant)}
                  className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-lg transition-all cursor-pointer flex flex-col"
                >
                  <div className="relative h-48">
                    <img
                      src={restaurant.image || '/images/default.png'}
                      alt={restaurant.name}

                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-3 right-3 bg-white px-3 py-1 rounded-full text-sm">
                      ⭐ {restaurant.rating}
                    </div>
                    <div className="absolute bottom-3 left-3 bg-primary-orange/90 text-white px-3 py-1 rounded-full text-xs">
                      {restaurant.pickCount} picks
                    </div>
                  </div>
                  <div className="p-4 flex flex-col h-full">
                    <div className="flex-1">
                      <h4 className="mb-1">{restaurant.name}</h4>
                      <p className="text-sm text-neutral-600 mb-2">
                        {restaurant.cuisine} • {formatPriceRange(restaurant.priceRange)}
                      </p>
                      <div className="flex items-center justify-between text-xs text-neutral-500 mb-2">
                        <div className="flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          <span>{restaurant.distance}</span>
                        </div>
                        <span>{restaurant.hours}</span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleAddRestaurantToShortlist(e, restaurant)}
                      disabled={addingToRoom === restaurant.id || restaurantsInShortlist.has(restaurant.id)}
                      className={`w-full mt-auto py-2 rounded-full transition-all text-sm disabled:cursor-not-allowed ${restaurantsInShortlist.has(restaurant.id)
                        ? 'bg-neutral-100 text-neutral-400'
                        : addingToRoom === restaurant.id
                          ? 'bg-gradient-to-r from-primary-orange to-primary-green text-white opacity-50'
                          : 'bg-gradient-to-r from-primary-orange to-primary-green text-white hover:shadow-md'
                        }`}
                    >
                      {addingToRoom === restaurant.id
                        ? 'Adding...'
                        : restaurantsInShortlist.has(restaurant.id)
                          ? 'In Shortlist'
                          : 'Add to Room Shortlist'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          <AllRestaurantsMap
            restaurants={sortedRestaurants}
            onRestaurantClick={handleRestaurantClick}
          />
        )}
      </main>

      {/* Add Restaurant Form Modal */}
      {showAddRestaurant && (
        <AddRestaurantForm
          onClose={() => setShowAddRestaurant(false)}
          onSuccess={handleRestaurantAdded}
        />
      )}
    </div>
  );
}
