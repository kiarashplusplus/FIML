/**
 * Shared TypeScript type definitions for FIML Mobile
 */

// ============================================================================
// Provider Types
// ============================================================================

export interface Provider {
    name: string;
    displayName: string;
    isConnected: boolean;
    description?: string;
    tier?: 'free' | 'premium' | 'enterprise';
}

export interface ProviderInfo {
    name: string;
    displayName: string;
    description: string;
    needsSecret: boolean;
    tier?: 'free' | 'premium' | 'enterprise';
}

// ============================================================================
// API Response Types
// ============================================================================

export interface KeyManagementResponse {
    success: boolean;
    message?: string;
    error?: string;
}

export interface ValidationResponse {
    valid: boolean;
    message?: string;
    expected_pattern?: string;
    key_length?: number;
}

export interface ProviderStatusResponse {
    providers: Provider[];
}

// ============================================================================
// User Types
// ============================================================================

export interface User {
    id: string;
    name: string;
    email?: string;
    platform?: 'mobile' | 'web' | 'telegram';
}

// ============================================================================
// Chat/Message Types
// ============================================================================

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    actions?: MessageAction[];
}

export interface MessageAction {
    text: string;
    action: string;
    type: 'primary' | 'secondary';
}

// ============================================================================
// Onboarding Types
// ============================================================================

export interface OnboardingSlide {
    id: string;
    title: string;
    description: string;
    icon: string;
}

// ============================================================================
// Component Props Types
// ============================================================================

export interface ProviderKeyCardProps {
    provider: Provider;
    onAdd: (providerName: string) => void;
    onTest: (providerName: string) => Promise<void>;
    onRemove: (providerName: string) => void;
}

export interface AddKeyModalProps {
    visible: boolean;
    providerName: string;
    providerDisplayName: string;
    onClose: () => void;
    onSubmit: (providerName: string, apiKey: string, apiSecret?: string) => Promise<void>;
}

// ============================================================================
// Usage Statistics Types
// ============================================================================

export interface UsageStats {
    provider: string;
    daily_usage: number;
    daily_limit: number;
    monthly_usage: number;
    monthly_limit: number;
    daily_percentage: number;
    monthly_percentage: number;
    warning: boolean;
    tier: string;
}

export interface UsageStatsResponse {
    stats: UsageStats[];
    total_calls_today: number;
    has_warnings: boolean;
    timestamp: string;
}
