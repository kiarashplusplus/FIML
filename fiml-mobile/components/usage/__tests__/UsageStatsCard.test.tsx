import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import UsageStatsCard from '../UsageStatsCard';
import { UsageStatsResponse } from '../../../types';

describe('UsageStatsCard', () => {
    const mockStats: UsageStatsResponse = {
        stats: [
            {
                provider: 'alpha_vantage',
                daily_usage: 150,
                daily_limit: 500,
                monthly_usage: 1000,
                monthly_limit: 15000,
                daily_percentage: 30,
                monthly_percentage: 6.6,
                warning: false,
                tier: 'free'
            }
        ],
        total_calls_today: 150,
        has_warnings: false,
        timestamp: new Date().toISOString()
    };

    it('renders nothing when stats are null', () => {
        const { toJSON } = render(
            <UsageStatsCard stats={null} loading={false} onRefresh={() => { }} />
        );
        expect(toJSON()).toBeNull();
    });

    it('renders correctly with stats', () => {
        const { getByText } = render(
            <UsageStatsCard stats={mockStats} loading={false} onRefresh={() => { }} />
        );
        expect(getByText('📊 API Usage')).toBeTruthy();
        expect(getByText('150')).toBeTruthy();
        expect(getByText('alpha_vantage')).toBeTruthy();
    });

    it('shows warning banner when has_warnings is true', () => {
        const warningStats = { ...mockStats, has_warnings: true };
        const { getByText } = render(
            <UsageStatsCard stats={warningStats} loading={false} onRefresh={() => { }} />
        );
        expect(getByText('⚠️ Approaching Quota Limits')).toBeTruthy();
    });

    it('calls onRefresh when refresh button is pressed', () => {
        const onRefresh = jest.fn();
        const { getByText } = render(
            <UsageStatsCard stats={mockStats} loading={false} onRefresh={onRefresh} />
        );

        fireEvent.press(getByText('🔄'));
        expect(onRefresh).toHaveBeenCalled();
    });

    it('shows loading state', () => {
        const { getByText } = render(
            <UsageStatsCard stats={mockStats} loading={true} onRefresh={() => { }} />
        );
        expect(getByText('...')).toBeTruthy();
    });
});
