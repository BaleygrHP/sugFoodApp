CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS restaurants (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cuisine VARCHAR(100) NOT NULL,
    price_range VARCHAR(20) NOT NULL DEFAULT '$',
    rating DECIMAL(4, 2) NOT NULL DEFAULT 4.00,
    distance VARCHAR(50) NOT NULL DEFAULT '0.5 km',
    hours VARCHAR(100) NOT NULL DEFAULT '09:00-21:00',
    address TEXT NOT NULL,
    image VARCHAR(500),
    description TEXT,
    reviews INTEGER DEFAULT 0,
    pick_count INTEGER DEFAULT 0,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    normalized_name VARCHAR(255),
    service_mode VARCHAR(20) NOT NULL DEFAULT 'mixed',
    avg_price_min NUMERIC(10, 2),
    avg_price_max NUMERIC(10, 2),
    capacity INTEGER,
    delivery_radius_km NUMERIC(8, 2) DEFAULT 5,
    reliability_score NUMERIC(6, 4) NOT NULL DEFAULT 0.8,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    supports_invoice BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS normalized_name VARCHAR(255);
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS service_mode VARCHAR(20) NOT NULL DEFAULT 'mixed';
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS avg_price_min NUMERIC(10, 2);
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS avg_price_max NUMERIC(10, 2);
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS capacity INTEGER;
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS delivery_radius_km NUMERIC(8, 2) DEFAULT 5;
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS reliability_score NUMERIC(6, 4) NOT NULL DEFAULT 0.8;
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS supports_invoice BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_restaurants_cuisine ON restaurants(cuisine);
CREATE INDEX IF NOT EXISTS idx_restaurants_price_range ON restaurants(price_range);
CREATE INDEX IF NOT EXISTS idx_restaurants_rating ON restaurants(rating);
CREATE INDEX IF NOT EXISTS idx_restaurants_location ON restaurants(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_restaurants_status_mode ON restaurants(status, service_mode);
CREATE INDEX IF NOT EXISTS idx_restaurants_normalized_name ON restaurants(normalized_name);

CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    restaurant_id VARCHAR(50) NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    image VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (restaurant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant_id ON menu_items(restaurant_id);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    account_status VARCHAR(20) NOT NULL DEFAULT 'guest',
    role VARCHAR(20) NOT NULL DEFAULT 'guest',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferred_budget_min NUMERIC(10, 2),
    preferred_budget_max NUMERIC(10, 2),
    novelty_preference VARCHAR(20) NOT NULL DEFAULT 'balanced',
    dining_mode_preference VARCHAR(20) NOT NULL DEFAULT 'mixed',
    work_lat NUMERIC(10, 8),
    work_lng NUMERIC(11, 8),
    restrictions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    blocked_restaurant_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    favorite_restaurant_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    favorite_dish_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    cuisine_preferences_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    dish_style_preferences_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    preference_version INT NOT NULL DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cuisines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS dishes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    cuisine_id UUID REFERENCES cuisines(id) ON DELETE SET NULL,
    tags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dishes_normalized_name ON dishes(normalized_name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dishes_normalized_name_unique ON dishes(normalized_name);

CREATE TABLE IF NOT EXISTS restaurant_dishes (
    restaurant_id VARCHAR(50) NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    dish_id UUID NOT NULL REFERENCES dishes(id) ON DELETE CASCADE,
    current_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (restaurant_id, dish_id)
);

CREATE INDEX IF NOT EXISTS idx_restaurant_dishes_restaurant_active ON restaurant_dishes(restaurant_id, active);

CREATE TABLE IF NOT EXISTS rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    name VARCHAR(255),
    host_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    meal_type VARCHAR(20) NOT NULL DEFAULT 'lunch',
    mode VARCHAR(20) NOT NULL DEFAULT 'mixed',
    location_label VARCHAR(255),
    target_lat NUMERIC(10, 8),
    target_lng NUMERIC(11, 8),
    group_size_expected INT NOT NULL DEFAULT 3,
    budget_min NUMERIC(10, 2),
    budget_max NUMERIC(10, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    expires_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE rooms ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS host_user_id UUID;
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS meal_type VARCHAR(20) NOT NULL DEFAULT 'lunch';
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS mode VARCHAR(20) NOT NULL DEFAULT 'mixed';
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS location_label VARCHAR(255);
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS target_lat NUMERIC(10, 8);
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS target_lng NUMERIC(11, 8);
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS group_size_expected INT NOT NULL DEFAULT 3;
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS budget_min NUMERIC(10, 2);
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS budget_max NUMERIC(10, 2);
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_rooms_status_expires ON rooms(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_rooms_host ON rooms(host_user_id);

CREATE TABLE IF NOT EXISTS participants (
    id UUID NOT NULL,
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    name VARCHAR(100),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, room_id)
);

CREATE INDEX IF NOT EXISTS idx_participants_room ON participants(room_id);

CREATE TABLE IF NOT EXISTS room_members (
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    participation_status VARCHAR(20) NOT NULL DEFAULT 'joined',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (room_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_room_members_room_user ON room_members(room_id, user_id);

CREATE TABLE IF NOT EXISTS room_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    invite_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS room_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    free_text_input TEXT,
    selected_suggestions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    normalized_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    hard_constraints_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ranked_choices_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    prefill_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (room_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_room_preferences_room_user ON room_preferences(room_id, user_id);

CREATE TABLE IF NOT EXISTS recommendation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    algorithm_version VARCHAR(100) NOT NULL,
    config_version VARCHAR(100) NOT NULL,
    request_context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'success'
);

CREATE INDEX IF NOT EXISTS idx_recommendation_runs_room_started ON recommendation_runs(room_id, started_at DESC);

CREATE TABLE IF NOT EXISTS recommendation_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_run_id UUID NOT NULL REFERENCES recommendation_runs(id) ON DELETE CASCADE,
    candidate_type VARCHAR(30) NOT NULL,
    candidate_ref_id VARCHAR(255),
    composite_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    base_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    final_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    confidence NUMERIC(10, 6) NOT NULL DEFAULT 0,
    rank_position INT NOT NULL,
    explanation_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    selected_for_vote BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_recommendation_candidates_run_rank ON recommendation_candidates(recommendation_run_id, rank_position);

CREATE TABLE IF NOT EXISTS recommendation_user_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_run_id UUID NOT NULL REFERENCES recommendation_runs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES recommendation_candidates(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preference_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    frequency_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    familiarity_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    context_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    budget_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    reliability_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    social_affinity_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    novelty_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    cooldown_penalty NUMERIC(10, 6) NOT NULL DEFAULT 0,
    friction_penalty NUMERIC(10, 6) NOT NULL DEFAULT 0,
    final_personal_score NUMERIC(10, 6) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS final_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    recommendation_run_id UUID NOT NULL REFERENCES recommendation_runs(id) ON DELETE CASCADE,
    decision_type VARCHAR(30) NOT NULL,
    selected_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence_score NUMERIC(10, 6) NOT NULL DEFAULT 0,
    decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meal_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    room_id UUID REFERENCES rooms(id) ON DELETE SET NULL,
    restaurant_id VARCHAR(50) REFERENCES restaurants(id) ON DELETE SET NULL,
    dish_id UUID REFERENCES dishes(id) ON DELETE SET NULL,
    chosen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    satisfaction_score NUMERIC(4, 2)
);

CREATE INDEX IF NOT EXISTS idx_meal_history_user_chosen_at ON meal_history(user_id, chosen_at DESC);
CREATE INDEX IF NOT EXISTS idx_meal_history_room_chosen_at ON meal_history(room_id, chosen_at DESC);

CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id VARCHAR(50) NOT NULL UNIQUE REFERENCES restaurants(id) ON DELETE CASCADE,
    source_system VARCHAR(100),
    external_ref VARCHAR(255),
    account_manager VARCHAR(255),
    active_contract BOOLEAN NOT NULL DEFAULT TRUE,
    approval_status VARCHAR(20) NOT NULL DEFAULT 'approved',
    invoice_supported BOOLEAN NOT NULL DEFAULT FALSE,
    supports_delivery BOOLEAN NOT NULL DEFAULT TRUE,
    supports_dine_in BOOLEAN NOT NULL DEFAULT TRUE,
    reliability_score NUMERIC(10, 6) NOT NULL DEFAULT 0.8,
    delivery_sla_mins NUMERIC(10, 2),
    notes TEXT,
    imported_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vendor_metrics_daily (
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    orders_count INT NOT NULL DEFAULT 0,
    cancel_rate NUMERIC(10, 6) NOT NULL DEFAULT 0,
    avg_delivery_mins NUMERIC(10, 2),
    complaint_rate NUMERIC(10, 6) NOT NULL DEFAULT 0,
    reliability_score NUMERIC(10, 6) NOT NULL DEFAULT 0.8,
    PRIMARY KEY (vendor_id, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_vendor_metrics_daily_vendor_date ON vendor_metrics_daily(vendor_id, metric_date DESC);

CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    room_id UUID REFERENCES rooms(id) ON DELETE SET NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    app_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS room_menu_items (
    id SERIAL PRIMARY KEY,
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    menu_item_id INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (room_id, menu_item_id)
);

CREATE INDEX IF NOT EXISTS idx_room_menu_items_room ON room_menu_items(room_id);

ALTER TABLE IF EXISTS votes ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE IF EXISTS votes ADD COLUMN IF NOT EXISTS recommendation_candidate_id UUID;
ALTER TABLE IF EXISTS votes ADD COLUMN IF NOT EXISTS vote_value NUMERIC(10, 2);

CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
    participant_id UUID,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recommendation_candidate_id UUID REFERENCES recommendation_candidates(id) ON DELETE CASCADE,
    vote_value NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (room_id, participant_id, menu_item_id)
);

CREATE INDEX IF NOT EXISTS idx_votes_room ON votes(room_id);
CREATE INDEX IF NOT EXISTS idx_votes_menu_item ON votes(menu_item_id);
CREATE INDEX IF NOT EXISTS idx_votes_room_user ON votes(room_id, user_id);
