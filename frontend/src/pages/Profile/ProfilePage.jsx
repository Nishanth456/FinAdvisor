import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../api/axios';
import styles from './ProfilePage.module.css';

const ProfilePage = () => {
    const { user, updateProfile } = useAuth();
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        date_of_birth: '',
        monthly_income: '',
        monthly_expenses: '',
        risk_appetite: 'Medium',
        investment_horizon_years: 5,
        financial_goals: ['Retirement'],
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        // If user already has a profile, load their data
        if (user?.has_profile) {
        // In a real app, you would fetch the profile data from the API
        // For now, we'll just pre-fill with some default values
        setFormData(prev => ({
            ...prev,
            ...user.profile // Assuming profile data is nested under user.profile
        }));
        }
    }, [user]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleNumberChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: parseFloat(value) || '' }));
    };

    const handleGoalChange = (e) => {
        const { value, checked } = e.target;
        setFormData(prev => {
        const goals = [...prev.financial_goals];
        if (checked) {
            goals.push(value);
        } else {
            const index = goals.indexOf(value);
            if (index > -1) {
            goals.splice(index, 1);
            }
        }
        return { ...prev, financial_goals: goals };
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        
        try {
            // Format the data before sending
            const formattedData = {
                ...formData,
                monthly_income: parseFloat(formData.monthly_income),
                monthly_expenses: parseFloat(formData.monthly_expenses),
                investment_horizon_years: parseInt(formData.investment_horizon_years, 10),
                financial_goals: [...formData.financial_goals],
                // Ensure risk_appetite is properly formatted (should already be from radio buttons)
                risk_appetite: formData.risk_appetite && typeof formData.risk_appetite === 'string' 
                  ? formData.risk_appetite.trim() 
                  : 'Medium' // Default to Medium if not set
            };
            
            console.log('Submitting profile data:', formattedData);
            
            try {
                console.log('[4] Calling updateProfile API...');
                const result = await updateProfile(formattedData);
                console.log('[5] API Response:', JSON.stringify(result, null, 2));
                
                if (result && (result.success || result.profile_updated)) {
                    console.log('[6] Profile update successful');
                    alert('Profile updated successfully!');
                    navigate('/dashboard');
                    return;
                } else {
                    console.error('[6] Profile update failed with result:', result);
                    const errorMessage = typeof result?.error === 'object' ? 
                        JSON.stringify(result.error) : 
                        (result?.error || 'Failed to update profile');
                    throw new Error(errorMessage);
                }
            } catch (apiError) {
                console.error('[API Error]', apiError);
                throw apiError; // Re-throw to be caught by the outer catch
            }
        } catch (err) {
            console.error('[7] Error caught in handleSubmit:', err);
            
            let errorMessage = 'An unknown error occurred';
            let errorDetails = '';
            
            try {
                // Try to extract meaningful error information
                if (err.response) {
                    // The request was made and the server responded with an error status
                    const responseData = err.response.data || {};
                    console.error('Response data:', responseData);
                    console.error('Response status:', err.response.status);
                    
                    errorMessage = responseData.detail || 
                                 responseData.message || 
                                 `Server error (${err.response.status})`;
                    
                    // Include additional error details if available
                    if (responseData.detail) {
                        errorDetails = `Details: ${responseData.detail}`;
                    }
                } else if (err.request) {
                    // The request was made but no response was received
                    console.error('No response received:', err.request);
                    errorMessage = 'No response from server. Please check your connection.';
                } else {
                    // Something happened in setting up the request
                    console.error('Error setting up request:', err.message);
                    errorMessage = err.message || 'Error setting up the request';
                }
                
                // If we have an error object, try to stringify it for display
                if (err instanceof Error) {
                    console.error('Error stack:', err.stack);
                    errorDetails = err.stack || errorDetails;
                } else if (typeof err === 'object') {
                    errorDetails = JSON.stringify(err, null, 2);
                }
                
                console.error('Full error object:', JSON.stringify(err, Object.getOwnPropertyNames(err)));
                
            } catch (logError) {
                console.error('Error while processing error:', logError);
                errorMessage = 'An error occurred while processing your request';
            }
            
            // Set the error message in state for display in the UI
            setError(`${errorMessage} ${errorDetails ? `\n\n${errorDetails}` : ''}`);
            
            // Also show an alert with the error
            alert(`Error: ${errorMessage}${errorDetails ? '\n\nSee below for details.' : ''}`);
        } finally {
            setLoading(false);
        }
    };

    const financialGoals = [
        { value: 'Retirement', label: 'Retirement' },
        { value: 'Buying a House', label: 'Buying a House' },
        { value: 'Education', label: 'Education' },
        { value: 'Wealth Building', label: 'Wealth Building' },
        { value: 'Travel', label: 'Travel' },
        { value: 'Emergency Fund', label: 'Emergency Fund' },
    ];

    return (
        <div className={styles.profileContainer}>
        <div className={styles.profileCard}>
            <h1>Complete Your Profile</h1>
            <p className={styles.subtitle}>Tell us about your financial situation to get personalized recommendations.</p>
            
            {error && <div className={styles.error}>{error}</div>}

            <form onSubmit={handleSubmit} className={styles.profileForm}>
            <div className={styles.formRow}>
                <div className={styles.formGroup}>
                <label htmlFor="date_of_birth">Date of Birth</label>
                <input
                    type="date"
                    id="date_of_birth"
                    name="date_of_birth"
                    value={formData.date_of_birth}
                    onChange={handleChange}
                    required
                    className={styles.formInput}
                    disabled={loading}
                />
                </div>

                <div className={styles.formGroup}>
                <label htmlFor="monthly_income">Monthly Income ($)</label>
                <input
                    type="number"
                    id="monthly_income"
                    name="monthly_income"
                    value={formData.monthly_income}
                    onChange={handleNumberChange}
                    min="0"
                    step="0.01"
                    required
                    className={styles.formInput}
                    disabled={loading}
                />
                </div>
            </div>

            <div className={styles.formRow}>
                <div className={styles.formGroup}>
                <label htmlFor="monthly_expenses">Monthly Expenses ($)</label>
                <input
                    type="number"
                    id="monthly_expenses"
                    name="monthly_expenses"
                    value={formData.monthly_expenses}
                    onChange={handleNumberChange}
                    min="0"
                    step="0.01"
                    required
                    className={styles.formInput}
                    disabled={loading}
                />
                </div>

                <div className={styles.formGroup}>
                <label htmlFor="investment_horizon_years">Investment Horizon (Years)</label>
                <input
                    type="number"
                    id="investment_horizon_years"
                    name="investment_horizon_years"
                    value={formData.investment_horizon_years}
                    onChange={handleNumberChange}
                    min="1"
                    max="50"
                    required
                    className={styles.formInput}
                    disabled={loading}
                />
                </div>
            </div>

            <div className={styles.formGroup}>
                <label>Risk Appetite</label>
                <div className={styles.radioGroup}>
                {['Low', 'Medium', 'High'].map(level => (
                    <label key={level} className={styles.radioLabel}>
                        <input
                            type="radio"
                            name="risk_appetite"
                            value={level}
                            checked={formData.risk_appetite === level}
                            onChange={handleChange}
                            disabled={loading}
                            className={styles.radioInput}
                        />
                        <span>{level}</span>
                    </label>
                ))}
                </div>
            </div>

            <div className={styles.formGroup}>
                <label>Financial Goals</label>
                <div className={styles.checkboxGroup}>
                {financialGoals.map((goal) => (
                    <label key={goal.value} className={styles.checkboxLabel}>
                    <input
                        type="checkbox"
                        value={goal.value}
                        checked={formData.financial_goals.includes(goal.value)}
                        onChange={handleGoalChange}
                        disabled={loading}
                        className={styles.checkboxInput}
                    />
                    <span>{goal.label}</span>
                    </label>
                ))}
                </div>
            </div>

            <div className={styles.formActions}>
                <button
                type="submit"
                className={styles.submitButton}
                disabled={loading}
                >
                {loading ? 'Saving...' : 'Save Profile'}
                </button>
            </div>
            </form>
        </div>
        </div>
    );
};

export default ProfilePage;