"use client";
import React, { useState, useEffect } from 'react';
import { Users } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { fetchRoom } from '@/lib/api';

export default function GroupOrderBubble() {
  const [currentRoomId, setCurrentRoomId] = useState<string | null>(null);
  const router = useRouter();

  // Load current room ID from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedRoomId = localStorage.getItem('current_room_id');
      if (storedRoomId) {
        // Verify room still exists and is open
        fetchRoom(storedRoomId)
          .then(room => {
            if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
              setCurrentRoomId(storedRoomId);
            } else {
              localStorage.removeItem('current_room_id');
              setCurrentRoomId(null);
            }
          })
          .catch(() => {
            localStorage.removeItem('current_room_id');
            setCurrentRoomId(null);
          });
      } else {
        setCurrentRoomId(null);
      }
    }
  }, []);

  // Poll localStorage to detect changes in the same tab (when room is created)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const interval = setInterval(() => {
      const storedRoomId = localStorage.getItem('current_room_id');
      
      // If we have a stored room ID but no current room ID, load it
      if (storedRoomId && storedRoomId !== currentRoomId) {
        fetchRoom(storedRoomId)
          .then(room => {
            if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
              setCurrentRoomId(storedRoomId);
            } else {
              localStorage.removeItem('current_room_id');
              setCurrentRoomId(null);
            }
          })
          .catch(() => {
            localStorage.removeItem('current_room_id');
            setCurrentRoomId(null);
          });
      }
      // If localStorage is empty but we have a current room ID, clear it
      else if (!storedRoomId && currentRoomId) {
        setCurrentRoomId(null);
      }
    }, 1000); // Check every second

    return () => clearInterval(interval);
  }, [currentRoomId]);

  // Listen for storage changes (when room is created/closed in other tabs)
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'current_room_id') {
        if (e.newValue) {
          fetchRoom(e.newValue)
            .then(room => {
              if (room.status === 'open' || room.status === 'ranking' || room.status === 'voting') {
                setCurrentRoomId(e.newValue);
              } else {
                setCurrentRoomId(null);
              }
            })
            .catch(() => {
              setCurrentRoomId(null);
            });
        } else {
          setCurrentRoomId(null);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Poll for room status changes (in case room is closed)
  useEffect(() => {
    if (!currentRoomId) return;

    const interval = setInterval(() => {
      fetchRoom(currentRoomId)
        .then(room => {
          if (!(room.status === 'open' || room.status === 'ranking' || room.status === 'voting')) {
            localStorage.removeItem('current_room_id');
            setCurrentRoomId(null);
          }
        })
        .catch(() => {
          localStorage.removeItem('current_room_id');
          setCurrentRoomId(null);
        });
    }, 10000); // Check every 10 seconds

    return () => clearInterval(interval);
  }, [currentRoomId]);

  if (!currentRoomId) {
    return null;
  }

  return (
    <button
      onClick={() => router.push(`/voting/${currentRoomId}`)}
      className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-r from-primary-orange to-primary-green text-white rounded-full shadow-lg hover:shadow-xl transition-all flex items-center justify-center z-[9999] hover:scale-110 active:scale-95"
      title="Go to Group Order"
      aria-label="Go to Group Order"
    >
      <Users className="w-6 h-6" />
    </button>
  );
}

