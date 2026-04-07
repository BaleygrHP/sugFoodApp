"use client";
import React, { useState } from 'react';
import { Check, Star, ThumbsUp, MessageSquare, Camera, Upload, ArrowRight } from 'lucide-react';
import { Screen, Restaurant } from '../../app/page';
import Image from "next/image";
import { formatPriceRange } from '@/lib/format';
interface RatingScreenProps {
  restaurant: Restaurant;
  onNavigate: (screen: Screen) => void;
}

export default function RatingScreen({ restaurant, onNavigate }: RatingScreenProps) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [review, setReview] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [uploadedPhotos, setUploadedPhotos] = useState<number>(0);
  const [submitted, setSubmitted] = useState(false);

  const tags = [
    'Great Taste',
    'Fast Service',
    'Good Value',
    'Fresh Ingredients',
    'Large Portions',
    'Clean',
    'Friendly Staff',
    'Authentic'
  ];

  const handleTagToggle = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    // In real app, submit to backend
  };

  const handleFinish = () => {
    onNavigate('home');
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-green to-primary-orange flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-8 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-6">
            <Check className="w-10 h-10 text-green-600" />
          </div>

          <h1 className="mb-4">Thank You!</h1>
          <p className="text-neutral-600 mb-6">
            Your feedback helps the CLV community discover great food together.
          </p>

          <div className="bg-neutral-50 rounded-2xl p-6 mb-6">
            <div className="flex items-center gap-4 mb-4">
              <img
                src={restaurant.image || '/images/default.png'}
                alt={restaurant.name}
                className="w-16 h-16 rounded-xl object-cover"
              />
              <div className="text-left flex-1">
                <h4>{restaurant.name}</h4>
                <div className="flex items-center gap-1 mt-1">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-4 h-4 ${i < rating
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-neutral-300'
                        }`}
                    />
                  ))}
                </div>
              </div>
            </div>

            {selectedTags.length > 0 && (
              <div className="flex flex-wrap gap-2 justify-center">
                {selectedTags.map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1 bg-primary-orange/10 text-primary-orange rounded-full text-xs"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <button
              onClick={handleFinish}
              className="w-full bg-gradient-to-r from-primary-orange to-primary-green text-white py-3 rounded-full hover:shadow-lg transition-all"
            >
              Back to Home
            </button>
            <button
              onClick={() => setSubmitted(false)}
              className="w-full text-neutral-600 hover:text-neutral-900 text-sm"
            >
              Edit Review
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <div className="text-center mb-4">
            <h1 className="mb-2">Rate Your Experience</h1>
            <p className="text-neutral-600">Help others make better choices</p>
          </div>

          {/* Restaurant Info */}
          <div className="bg-neutral-50 rounded-2xl p-4 flex items-center gap-4">
            <img
              src={restaurant.image || '/images/default.png'}
              alt={restaurant.name}
              className="w-20 h-20 rounded-xl object-cover"
            />
            <div className="flex-1">
              <h4>{restaurant.name}</h4>
              <p className="text-sm text-neutral-600">{restaurant.cuisine} • {formatPriceRange(restaurant.priceRange)}</p>
            </div>
            <div className="text-center">
              <div className="flex items-center gap-1 mb-1">
                <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                <span className="text-sm">{restaurant.rating}</span>
              </div>
              <p className="text-xs text-neutral-500">{restaurant.reviews} reviews</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-4 py-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Star Rating */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h4 className="mb-4 text-center">Overall Rating</h4>
            <div className="flex items-center justify-center gap-2 mb-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="transition-transform hover:scale-110"
                >
                  <Star
                    className={`w-12 h-12 ${star <= (hoverRating || rating)
                      ? 'fill-yellow-400 text-yellow-400'
                      : 'text-neutral-300'
                      }`}
                  />
                </button>
              ))}
            </div>
            <p className="text-center text-sm text-neutral-600">
              {rating === 0 && 'Tap to rate'}
              {rating === 1 && 'Poor'}
              {rating === 2 && 'Fair'}
              {rating === 3 && 'Good'}
              {rating === 4 && 'Very Good'}
              {rating === 5 && 'Excellent'}
            </p>
          </div>

          {/* Quick Tags */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <ThumbsUp className="w-5 h-5 text-primary-orange" />
              <h4>What did you like?</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => handleTagToggle(tag)}
                  className={`px-4 py-2 rounded-full text-sm transition-all ${selectedTags.includes(tag)
                    ? 'bg-primary-orange text-white shadow-md'
                    : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
                    }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Written Review */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <MessageSquare className="w-5 h-5 text-primary-green" />
              <h4>Share Your Thoughts</h4>
              <span className="text-xs text-neutral-500 ml-auto">Optional</span>
            </div>
            <textarea
              placeholder="Tell us about your experience... What did you order? How was the service?"
              value={review}
              onChange={(e) => setReview(e.target.value)}
              rows={4}
              className="w-full px-4 py-3 border border-neutral-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-orange focus:border-transparent resize-none"
            />
            <p className="text-xs text-neutral-500 mt-2">
              {review.length} / 500 characters
            </p>
          </div>

          {/* Photo Upload */}
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Camera className="w-5 h-5 text-primary-orange" />
              <h4>Add Photos</h4>
              <span className="text-xs text-neutral-500 ml-auto">Optional</span>
            </div>

            {uploadedPhotos > 0 ? (
              <div className="grid grid-cols-3 gap-3 mb-3">
                {[...Array(uploadedPhotos)].map((_, i) => (
                  <div
                    key={i}
                    className="aspect-square bg-neutral-100 rounded-xl flex items-center justify-center"
                  >
                    <Camera className="w-8 h-8 text-neutral-400" />
                  </div>
                ))}
              </div>
            ) : null}

            <button
              type="button"
              onClick={() => setUploadedPhotos(prev => prev + 1)}
              className="w-full py-3 border-2 border-dashed border-neutral-300 rounded-2xl text-neutral-600 hover:border-primary-orange hover:text-primary-orange transition-all flex items-center justify-center gap-2"
            >
              <Upload className="w-5 h-5" />
              <span>Upload Photos</span>
            </button>
            <p className="text-xs text-neutral-500 mt-2 text-center">
              Help others see what to expect
            </p>
          </div>

          {/* Privacy Notice */}
          <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4">
            <p className="text-sm text-blue-900">
              🔒 Your review will be visible to other CLV employees and helps build our internal restaurant database.
            </p>
          </div>

          {/* Submit Button */}
          <div className="sticky bottom-0 bg-white border-t border-neutral-200 p-4 rounded-2xl shadow-lg space-y-3">
            <button
              type="submit"
              disabled={rating === 0}
              className={`w-full py-4 rounded-full transition-all flex items-center justify-center gap-2 ${rating === 0
                ? 'bg-neutral-300 text-neutral-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-primary-orange to-primary-green text-white hover:shadow-lg'
                }`}
            >
              Submit Review
              <ArrowRight className="w-5 h-5" />
            </button>
            <button
              type="button"
              onClick={handleFinish}
              className="w-full py-3 text-neutral-600 hover:text-neutral-900 transition-colors text-sm"
            >
              Skip Rating
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
