import React from 'react';
import { render } from '@testing-library/react-native';
import UsageProgressBar from '../UsageProgressBar';
import { UsageStats } from '../../../types';

describe('UsageProgressBar', () => {
    const mockStat: UsageStats = {
        provider: 'alpha_vantage',
        daily_usage: 150,
        daily_limit: 500,
        monthly_usage: 1000,
        monthly_limit: 15000,
        daily_percentage: 30,
        monthly_percentage: 6.6,
        warning: false,
        tier: 'free'
    };

    it('renders provider name and usage correctly', () => {
        const { getByText } = render(<UsageProgressBar stat={mockStat} />);
        expect(getByText('alpha_vantage')).toBeTruthy();
        expect(getByText('150 / 500')).toBeTruthy();
        expect(getByText('free tier')).toBeTruthy();
    });

    it('shows warning color and message when warning is true', () => {
        const warningStat = { ...mockStat, warning: true, daily_percentage: 85 };
        const { getByText } = render(<UsageProgressBar stat={warningStat} />);

        expect(getByText('⚠️ 85% of daily limit')).toBeTruthy();
    });

    it('handles infinite limits correctly', () => {
        const infiniteStat = { ...mockStat, daily_limit: Infinity };
        const { getByText } = render(<UsageProgressBar stat={infiniteStat} />);
        expect(getByText('150 / ∞')).toBeTruthy();
    });
});
