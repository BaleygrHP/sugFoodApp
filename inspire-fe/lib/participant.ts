// Utility to manage participant ID in browser
// Each browser gets a unique participant ID stored in localStorage
// Must be a valid UUID format for database

function generateUUID(): string {
  // Generate UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export function getParticipantId(): string {
  if (typeof window === 'undefined') {
    // Server-side: generate a UUID
    return generateUUID();
  }

  const storageKey = 'participant_id';
  let participantId = localStorage.getItem(storageKey);

  if (!participantId) {
    // Generate a valid UUID
    participantId = generateUUID();
    localStorage.setItem(storageKey, participantId);
  }

  // Validate UUID format
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(participantId)) {
    // If stored ID is not valid UUID, generate new one
    participantId = generateUUID();
    localStorage.setItem(storageKey, participantId);
  }

  return participantId;
}

export function clearParticipantId(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('participant_id');
  }
}

