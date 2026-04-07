"use client";
import React, { useState, useEffect, useRef } from 'react';
import { X, Plus, Trash2, MapPin, Upload, Image as ImageIcon } from 'lucide-react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { createRestaurant, uploadImage, type CreateRestaurantData } from '@/lib/api';
import { toast } from 'sonner';

interface AddRestaurantFormProps {
  onClose: () => void;
  onSuccess: () => void;
}

interface MenuItemInput {
  name: string;
  price: number;
}

export default function AddRestaurantForm({ onClose, onSuccess }: AddRestaurantFormProps) {
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [cuisine, setCuisine] = useState('Other');
  const [menuItems, setMenuItems] = useState<MenuItemInput[]>([{ name: '', price: 0 }]);
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [showMap, setShowMap] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const marker = useRef<mapboxgl.Marker | null>(null);

  // Initialize map
  useEffect(() => {
    if (!showMap || !mapContainer.current) return;

    const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
    if (!mapboxToken) {
      toast.error('Mapbox token not configured');
      return;
    }

    mapboxgl.accessToken = mapboxToken;

    // Initialize map centered on Ho Chi Minh City
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [106.6297, 10.8231], // Ho Chi Minh City
      zoom: 13,
    });

    // Add click handler to place marker
    map.current.on('click', (e) => {
      const { lng, lat } = e.lngLat;
      setLongitude(lng);
      setLatitude(lat);

      // Remove existing marker
      if (marker.current) {
        marker.current.remove();
      }

      // Add new marker
      marker.current = new mapboxgl.Marker({ color: '#f97316' })
        .setLngLat([lng, lat])
        .addTo(map.current!);
    });

    return () => {
      if (map.current) {
        map.current.remove();
      }
      if (marker.current) {
        marker.current.remove();
      }
    };
  }, [showMap]);

  const addMenuItem = () => {
    setMenuItems([...menuItems, { name: '', price: 0 }]);
  };

  const removeMenuItem = (index: number) => {
    setMenuItems(menuItems.filter((_, i) => i !== index));
  };

  const updateMenuItem = (index: number, field: 'name' | 'price', value: string | number) => {
    const updated = [...menuItems];
    updated[index] = { ...updated[index], [field]: value };
    setMenuItems(updated);
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        return;
      }
      
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        toast.error('Image size must be less than 5MB');
        return;
      }

      setImageFile(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      toast.error('Please enter restaurant name');
      return;
    }

    if (!address.trim()) {
      toast.error('Please enter address');
      return;
    }

    if (!latitude || !longitude) {
      toast.error('Please select location on map');
      return;
    }

    try {
      setSubmitting(true);

      const menuItemsData = menuItems
        .filter(item => item.name.trim() !== '')
        .map(item => ({
          name: item.name.trim(),
          price: item.price || 0,
        }));

      // Upload image if provided
      let imageUrl = undefined;
      if (imageFile) {
        try {
          imageUrl = await uploadImage(imageFile);
        } catch (error: any) {
          toast.error(error.message || 'Failed to upload image');
          setSubmitting(false);
          return;
        }
      }

      const data: CreateRestaurantData = {
        name: name.trim(),
        address: address.trim(),
        latitude,
        longitude,
        cuisine,
        menuItems: menuItemsData,
        image: imageUrl,
      };

      await createRestaurant(data);
      toast.success('Restaurant added successfully!');
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('Error creating restaurant:', error);
      toast.error(error.message || 'Failed to create restaurant');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-neutral-200 p-4 flex items-center justify-between z-10">
          <h2 className="text-xl font-semibold">Add New Restaurant</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-neutral-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Restaurant Name */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Restaurant Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-orange"
              placeholder="Enter restaurant name"
              required
            />
          </div>

          {/* Address */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Address *
            </label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-orange"
              placeholder="Enter address"
              required
            />
          </div>

          {/* Cuisine */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Cuisine Type
            </label>
            <select
              value={cuisine}
              onChange={(e) => setCuisine(e.target.value)}
              className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-orange"
            >
              <option value="Other">Other</option>
              <option value="Vietnamese">Vietnamese</option>
              <option value="Korean">Korean</option>
              <option value="Japanese">Japanese</option>
              <option value="Thai">Thai</option>
              <option value="Chinese">Chinese</option>
              <option value="Italian">Italian</option>
              <option value="American">American</option>
              <option value="Mexican">Mexican</option>
              <option value="Indian">Indian</option>
              <option value="Western">Western</option>
              <option value="Street Food">Street Food</option>
            </select>
          </div>

          {/* Image Upload */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Restaurant Image
            </label>
            {imagePreview ? (
              <div className="space-y-2">
                <div className="relative w-full h-48 rounded-lg overflow-hidden border border-neutral-300">
                  <img
                    src={imagePreview}
                    alt="Restaurant preview"
                    className="w-full h-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={removeImage}
                    className="absolute top-2 right-2 p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full px-4 py-2 border border-neutral-300 rounded-lg text-neutral-700 hover:bg-neutral-50 transition-colors text-sm"
                >
                  Change Image
                </button>
              </div>
            ) : (
              <div
                onClick={() => fileInputRef.current?.click()}
                className="w-full h-48 border-2 border-dashed border-neutral-300 rounded-lg flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-primary-orange hover:bg-primary-orange/5 transition-colors"
              >
                <ImageIcon className="w-10 h-10 text-neutral-400" />
                <span className="text-sm text-neutral-600">Click to upload image</span>
                <span className="text-xs text-neutral-500">PNG, JPG up to 5MB</span>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              className="hidden"
            />
          </div>

          {/* Map Picker */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Location on Map *
            </label>
            {!showMap ? (
              <button
                type="button"
                onClick={() => setShowMap(true)}
                className="w-full px-4 py-3 border-2 border-dashed border-primary-orange rounded-lg flex items-center justify-center gap-2 text-primary-orange hover:bg-primary-orange/5 transition-colors"
              >
                <MapPin className="w-5 h-5" />
                <span>Click to select location on map</span>
              </button>
            ) : (
              <div className="space-y-2">
                <div ref={mapContainer} className="w-full h-64 rounded-lg overflow-hidden border border-neutral-300" />
                {latitude && longitude && (
                  <p className="text-xs text-neutral-600">
                    Selected: {latitude.toFixed(6)}, {longitude.toFixed(6)}
                  </p>
                )}
                <button
                  type="button"
                  onClick={() => setShowMap(false)}
                  className="text-sm text-neutral-600 hover:text-neutral-900"
                >
                  Hide map
                </button>
              </div>
            )}
          </div>

          {/* Menu Items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-neutral-700">
                Menu Items
              </label>
              <button
                type="button"
                onClick={addMenuItem}
                className="flex items-center gap-1 text-sm text-primary-orange hover:text-primary-orange/80"
              >
                <Plus className="w-4 h-4" />
                Add Item
              </button>
            </div>
            <div className="space-y-2">
              {menuItems.map((item, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={item.name}
                    onChange={(e) => updateMenuItem(index, 'name', e.target.value)}
                    className="flex-1 px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-orange"
                    placeholder="Menu item name"
                  />
                  <input
                    type="number"
                    value={item.price || ''}
                    onChange={(e) => updateMenuItem(index, 'price', parseFloat(e.target.value) || 0)}
                    className="w-32 px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-orange"
                    placeholder="Price"
                    min="0"
                  />
                  {menuItems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeMenuItem(index)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-neutral-500 mt-2">
              Note: Price is in thousands (e.g., 50 = 50,000đ)
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-neutral-200">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-neutral-300 rounded-lg text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 px-4 py-2 bg-primary-orange text-white rounded-lg hover:bg-primary-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Adding...' : 'Add Restaurant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

