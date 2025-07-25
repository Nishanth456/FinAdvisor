import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../api/axios';
import styles from './DashboardPage.module.css';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
// Simple text-based icons
const RefreshIcon = () => <span>🔄</span>;
const DownloadIcon = () => <span>📥</span>;
const EmailIcon = () => <span>✉️</span>;
const WarningIcon = () => <span>⚠️</span>;
const CheckCircleIcon = () => <span>✓</span>;
const MagicWandIcon = () => <span>✨</span>;

// Helper function to format currency
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
};

const DashboardPage = () => {
  const { user, logout } = useAuth();
  const [recommendations, setRecommendations] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/api/recommendations');
      
      if (response.data && response.data.success && response.data.data) {
        const recData = response.data.data;
        
        // Format the last updated time
        if (response.data.created_at) {
          const updatedAt = new Date(response.data.created_at);
          setLastUpdated(updatedAt.toLocaleString());
        }
        
        // Helper function to get allocation percentage for an instrument type
        const getAllocationPercentage = (type) => {
          const allocationMap = {
            'stocks': recData.allocation_summary?.stocks || '0%',
            'mutual_funds': recData.allocation_summary?.mutual_funds || '0%',
            'fixed_deposits': recData.allocation_summary?.fixed_deposits || '0%'
          };
          return allocationMap[type] || '0%';
        };
        
        // Transform the data to match the frontend format
        const formattedRecommendation = {
          allocation_summary: Object.entries(recData.allocation_summary || {}).map(([key, value]) => ({
            name: key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
            value: typeof value === 'string' ? parseFloat(value.split('%')[0]) || 0 : value
          })),
          suggested_instruments: [
            ...((recData.suggested_instruments?.stocks || []).map(item => ({
              name: item.name || item.symbol || 'Unknown Stock',
              type: 'Stocks',
              symbol: item.symbol,
              sector: item.sector,
              growth: item.growth_pct_yoy ? `${item.growth_pct_yoy}%` : 'N/A',
              allocation: getAllocationPercentage('stocks')
            }))),
            ...((recData.suggested_instruments?.mutual_funds || []).map(item => ({
              name: item.name || `MF_${item.code || ''}`,
              type: 'Mutual Funds',
              category: item.category,
              returns: item.return_pct_3y_cagr ? `${item.return_pct_3y_cagr}%` : 'N/A',
              allocation: getAllocationPercentage('mutual_funds')
            }))),
            ...((recData.suggested_instruments?.fixed_deposits || []).map(item => ({
              name: item.bank || 'Fixed Deposit',
              type: 'Fixed Deposits',
              tenure: item.tenure_months ? `${item.tenure_months} months` : 'N/A',
              rate: item.rate_pct ? `${item.rate_pct}%` : 'N/A',
              allocation: getAllocationPercentage('fixed_deposits')
            })))
          ],
          explanation: recData.explanation || 'No explanation provided.',
          investment_plan: {
            monthly_investment: recData.investment_plan?.monthly_investment || 'Not specified',
            goal_breakdown: recData.investment_plan?.goal_breakdown || {},
            risk_management: recData.investment_plan?.risk_management || []
          },
          projected_returns: {
            conservative: recData.projected_returns?.conservative || 'N/A',
            moderate: recData.projected_returns?.moderate || 'N/A',
            aggressive: recData.projected_returns?.aggressive || 'N/A',
            // Handle both 'stocks' and 'stock' variations
            'expected_value for stocks': recData.projected_returns?.['expected_value for stocks'] || 
                                      recData.projected_returns?.['expected_value for stock'] || 'Not available',
            // Handle both 'mutual funds' and 'mutual_funds' variations
            'expected_value for mutual funds': recData.projected_returns?.['expected_value for mutual funds'] || 
                                            recData.projected_returns?.['expected_value for mutual_funds'] || 'Not available',
            // Handle both 'fixed deposits' and 'fixed_deposits' variations
            'expected_value for fixed deposits': recData.projected_returns?.['expected_value for fixed deposits'] || 
                                              recData.projected_returns?.['expected_value for fixed_deposits'] || 'Not available',
            // Handle both 'total expected_value' and 'total_expected_value' variations
            'total_expected_value': recData.projected_returns?.['total expected_value'] || 
                                 recData.projected_returns?.total_expected_value || 'Not available'
          }
        };
        
        setRecommendations(formattedRecommendation);
        setError(null);
      } else if (response.data && !response.data.success) {
        setError(response.data.message || 'No recommendations found.');
        setRecommendations(null);
      } else {
        setError('No recommendations found. Please generate recommendations first.');
        setRecommendations(null);
      }
    } catch (err) {
      console.error('Error fetching recommendations:', err);
      setError('Failed to load recommendations. ' + (err.response?.data?.detail || 'Please try again later.'));
    } finally {
      setLoading(false);
    }
  };

  const generateNewRecommendations = async () => {
    try {
      setGenerating(true);
      setError(null);
      setSuccessMessage('');
      
      const response = await api.post('/api/recommendations/generate');
      if (response.data && response.data.success) {
        // After generating, fetch the latest recommendations to ensure consistency
        await fetchRecommendations();
        setSuccessMessage('New recommendations have been successfully generated!');
        
        // Clear the success message after 5 seconds
        setTimeout(() => {
          setSuccessMessage('');
        }, 5000);
      } else {
        throw new Error(response.data?.detail || 'Failed to generate recommendations');
      }
    } catch (err) {
      console.error('Failed to generate recommendations:', err);
      setError('Failed to generate new recommendations. ' + (err.response?.data?.detail || err.message || 'Please try again later.'));
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const handleRefresh = () => {
    window.location.reload();
  };

  const handleSavePlan = () => {
    // Implement save plan functionality
    console.log('Saving plan...');
    // You can add download functionality here
    const element = document.createElement('a');
    const file = new Blob([JSON.stringify(recommendations, null, 2)], {type: 'application/json'});
    element.href = URL.createObjectURL(file);
    element.download = 'financial-plan.json';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleContactAdvisor = () => {
    // Implement contact advisor functionality
    console.log('Contacting advisor...');
    window.location.href = 'mailto:advisor@example.com?subject=Financial Advice Request';
  };

  console.log('Render - Loading:', loading, 'Recommendations:', recommendations);

  if (loading && !recommendations) {
    return (
      <div className={styles.dashboard}>
        <header className={styles.header}>
          <div>
            <h1>Welcome back, {user?.name || 'Investor'}</h1>
            <p>Preparing your financial dashboard</p>
          </div>
        </header>
        <div className={styles.loadingContainer}>
          <div className={styles.spinner}></div>
          <p>Analyzing your financial profile...</p>
          <p className={styles.loadingText}>Generating personalized recommendations based on your goals and risk profile...</p>
        </div>
      </div>
    );
  }

  if (error && !recommendations) {
    return (
      <div className={styles.dashboard}>
        <header className={styles.header}>
          <div>
            <h1>Welcome back, {user?.name || 'Investor'}</h1>
            <p>We couldn't load your recommendations</p>
            <div className={styles.actionButtons}>
              <button 
                onClick={generateNewRecommendations} 
                className={`${styles.button} ${generating ? styles.loading : ''}`}
                disabled={generating}
              >
                {generating ? 'Generating...' : 'Generate New Recommendations'}
              </button>
              <button 
                className={styles.secondaryButton}
                onClick={fetchRecommendations}
                disabled={loading}
              >
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </header>
        
        <div className={styles.errorContainer}>
          <div className={styles.errorIcon}>⚠️</div>
          <h2>Error Loading Recommendations</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!recommendations) {
    return (
      <div className={styles.dashboard}>
        <h1>Your Financial Dashboard</h1>
        <div className={styles.emptyState}>
          <p>No recommendations available. Please complete your profile first.</p>
          <button 
            className={styles.primaryButton}
            onClick={() => window.location.href = '/profile'}
          >
            Complete Your Profile
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div>
          <h1>Welcome back, {user?.name || 'Investor'}</h1>
          <p>Your personalized investment plan is ready</p>
          <div className={styles.statusContainer}>
            {successMessage && (
              <div className={styles.successMessage}>
                <span className={styles.successIcon}>✓</span> {successMessage}
              </div>
            )}
          </div>

        </div>
        <button 
          className={styles.refreshButton} 
          onClick={handleRefresh} 
          disabled={loading}
        >
          <RefreshIcon className={`${styles.refreshIcon} ${loading ? styles.spin : ''}`} />
          {loading ? 'Refreshing...' : 'Refresh Data'}
        </button>
      </header>
      
      {/* Portfolio Allocation Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>Portfolio Allocation</h2>
          <p className={styles.sectionSubtitle}>Diversified across asset classes based on your risk profile</p>
        </div>
        
        <div className={styles.allocationContainer}>
          {/* Pie Chart */}
          <div className={styles.pieChartContainer}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={recommendations.allocation_summary}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={120}
                  paddingAngle={2}
                  dataKey="value"
                  nameKey="name"
                  label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {recommendations.allocation_summary.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={`hsl(${index * 90}, 70%, 60%)`}
                      stroke={`hsl(${index * 90}, 70%, 50%)`}
                    />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value, name) => [`${value}%`, name]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          {/* Legend Boxes */}
          <div className={styles.legend}>
            {recommendations.allocation_summary.map((item, index) => (
              <div key={index} className={styles.legendItem}>
                <span 
                  className={styles.legendColor}
                  style={{ 
                    background: `linear-gradient(135deg, hsl(${index * 90}, 70%, 60%), hsl(${index * 90 + 20}, 70%, 50%))`
                  }}
                ></span>
                <span className={styles.legendLabel}>
                  <strong>{item.name}</strong>
                  <span className={styles.legendValue}>{item.value}%</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Recommended Instruments Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>Recommended Instruments</h2>
          <p className={styles.sectionSubtitle}>Carefully selected based on your financial goals and risk tolerance</p>
        </div>
        
        <div className={styles.instrumentsGrid}>
          {recommendations.suggested_instruments && recommendations.suggested_instruments.length > 0 ? (
            recommendations.suggested_instruments.map((instrument, index) => (
              <div key={index} className={styles.instrumentCard}>
                <div className={styles.instrumentHeader}>
                  <h3>{instrument.name} {instrument.symbol && `(${instrument.symbol})`}</h3>
                  <span className={`${styles.instrumentType} ${styles[instrument.type.toLowerCase().replace(' ', '-')]}`}>
                    {instrument.type}
                  </span>
                </div>
                <div className={styles.instrumentContent}>
                  <div className={styles.instrumentDetail}>
                    <span className={styles.detailLabel}>Allocation</span>
                    <span className={styles.detailValue}>{instrument.allocation || 'N/A'}</span>
                  </div>
                  
                  {/* Stock specific details */}
                  {instrument.type === 'Stocks' && (
                    <>
                      {instrument.sector && (
                        <div className={styles.instrumentDetail}>
                          <span className={styles.detailLabel}>Sector</span>
                          <span className={styles.detailValue}>{instrument.sector}</span>
                        </div>
                      )}
                      {instrument.growth && (
                        <div className={styles.instrumentDetail}>
                          <span className={styles.detailLabel}>Growth (YoY)</span>
                          <span className={styles.detailValue}>{instrument.growth}</span>
                        </div>
                      )}
                    </>
                  )}
                  
                  {/* Mutual Fund specific details */}
                  {instrument.type === 'Mutual Funds' && (
                    <>
                      {instrument.category && (
                        <div className={styles.instrumentDetail}>
                          <span className={styles.detailLabel}>Category</span>
                          <span className={styles.detailValue}>{instrument.category}</span>
                        </div>
                      )}
                      {instrument.returns && (
                        <div className={styles.instrumentDetail}>
                          <span className={styles.detailLabel}>3Y Returns (CAGR)</span>
                          <span className={styles.detailValue}>{instrument.returns}</span>
                        </div>
                      )}
                    </>
                  )}
                  
                  {/* Fixed Deposit specific details */}
                  {instrument.type === 'Fixed Deposits' && (
                    <>
                      {instrument.rate && (
                        <div className={styles.instrumentDetail}>
                          <span className={styles.detailLabel}>Interest Rate</span>
                          <span className={styles.detailValue}>{instrument.rate}</span>
                        </div>
                      )}
                      {instrument.tenure && (
                        <div className={styles.instrumentDetail}>
                          <span className={styles.detailLabel}>Tenure</span>
                          <span className={styles.detailValue}>{instrument.tenure}</span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))
          ) : (
            <p>No specific instruments recommended at this time.</p>
          )}
        </div>
      </section>

      {/* Investment Plan Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>Your Investment Plan</h2>
          <p className={styles.sectionSubtitle}>Tailored to help you achieve your financial goals</p>
        </div>
        
        <div className={styles.planDetails}>
          {recommendations.investment_plan?.monthly_investment && (
            <div className={styles.planHighlight}>
              <div className={styles.planHighlightContent}>
                <h3>Recommended Monthly Investment</h3>
                <p className={styles.planAmount}>{recommendations.investment_plan.monthly_investment}</p>
                <p className={styles.planNote}>Automatically adjusted based on your income and expenses</p>
              </div>
              <div className={styles.planVisual}>
                <div className={styles.planChart}>
                  {/* Placeholder for a small chart or visualization */}
                  <div className={styles.chartPlaceholder}></div>
                </div>
              </div>
            </div>
          )}
          
          {recommendations.investment_plan?.goal_breakdown && (
            <div className={styles.planSection}>
              <h3>Goal Breakdown</h3>
              <div className={styles.goalsGrid}>
                {Object.entries(recommendations.investment_plan.goal_breakdown).map(([key, goal]) => (
                  <div key={key} className={styles.goalCard}>
                    <WarningIcon className={styles.alertIcon} />
                    <div className={styles.goalContent}>
                      <h4>{goal.name}</h4>
                      <p className={styles.goalAmount}>{goal.amount}</p>
                      <p className={styles.goalTimeline}>
                        <span className={styles.goalTimelineLabel}>Timeline:</span> {goal.timeline || 'Long-term'}
                      </p>
                      {goal.strategy && (
                        <div className={styles.goalStrategy}>
                          <span className={styles.strategyLabel}>Strategy:</span> {goal.strategy}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {recommendations.investment_plan?.risk_management && (
            <div className={styles.planSection}>
              <h3>Risk Management Strategy</h3>
              <div className={styles.riskManagement}>
                <div className={styles.riskVisual}>
                  <div className={styles.riskMeter}>
                    <div 
                      className={styles.riskLevel} 
                      style={{ width: `${recommendations.investment_plan.risk_level || 50}%` }}
                    ></div>
                  </div>
                  <div className={styles.riskLabels}>
                    <span>Conservative</span>
                    <span>Moderate</span>
                    <span>Aggressive</span>
                  </div>
                </div>
                <ul className={styles.riskList}>
                  {recommendations.investment_plan.risk_management.map((item, index) => (
                    <li key={index}>
                      <span className={styles.riskBullet}>•</span> {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Projected Returns Section */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>Projected Returns</h2>
          <p className={styles.sectionSubtitle}>Estimated performance based on historical data and current market conditions</p>
        </div>
        
        <div className={styles.returnsContainer}>
          <div className={styles.returnsGrid}>
            {/* Risk-based Return Projections */}
            <div className={styles.returnsSection}>
              <h3 className={styles.returnsSectionTitle}>Risk-Based Projections</h3>
              <div className={styles.returnsGridInner}>
                {recommendations.projected_returns?.conservative && (
                  <div className={styles.returnCard}>
                    <div className={styles.returnContent}>
                      <h4 className={styles.returnLabel}>Conservative</h4>
                      <p className={styles.returnValue}>{recommendations.projected_returns.conservative}</p>
                      <p className={styles.returnNote}>Lower risk, stable returns</p>
                    </div>
                  </div>
                )}
                
                {recommendations.projected_returns?.moderate && (
                  <div className={styles.returnCard}>
                    <div className={styles.returnContent}>
                      <h4 className={styles.returnLabel}>Moderate</h4>
                      <p className={styles.returnValue}>{recommendations.projected_returns.moderate}</p>
                      <p className={styles.returnNote}>Balanced risk and return</p>
                    </div>
                  </div>
                )}
                
                {recommendations.projected_returns?.aggressive && (
                  <div className={styles.returnCard}>
                    <div className={styles.returnContent}>
                      <h4 className={styles.returnLabel}>Aggressive</h4>
                      <p className={styles.returnValue}>{recommendations.projected_returns.aggressive}</p>
                      <p className={styles.returnNote}>Higher risk, potential for higher returns</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Expected Value Projections */}
            <div className={styles.returnsSection}>
              <h3 className={styles.returnsSectionTitle}>Expected Value Projections</h3>
              <div className={styles.expectedValueGrid}>
                {recommendations.projected_returns?.['expected_value for stocks'] && (
                  <div className={styles.expectedValueCard}>
                    <div className={styles.expectedValueContent}>
                      <h4>Stocks</h4>
                      <p className={styles.expectedValue}>
                        {recommendations.projected_returns['expected_value for stocks']}
                      </p>
                    </div>
                  </div>
                )}
                
                {recommendations.projected_returns?.['expected_value for mutual funds'] && (
                  <div className={styles.expectedValueCard}>
                    <div className={styles.expectedValueContent}>
                      <h4>Mutual Funds</h4>
                      <p className={styles.expectedValue}>
                        {recommendations.projected_returns['expected_value for mutual funds']}
                      </p>
                    </div>
                  </div>
                )}
                
                {recommendations.projected_returns?.['expected_value for fixed deposits'] && (
                  <div className={styles.expectedValueCard}>
                    <div className={styles.expectedValueContent}>
                      <h4>Fixed Deposits</h4>
                      <p className={styles.expectedValue}>
                        {recommendations.projected_returns['expected_value for fixed deposits']}
                      </p>
                    </div>
                  </div>
                )}
                
                {recommendations.projected_returns?.total_expected_value && (
                  <div className={`${styles.expectedValueCard} ${styles.highlightCard}`}>
                    <div className={styles.expectedValueContent}>
                      <h4>Total Portfolio Value</h4>
                      <p className={styles.expectedValueHighlight}>
                        {recommendations.projected_returns.total_expected_value}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div className={styles.returnsDisclaimer}>
            <p>Projections are estimates only and not guaranteed. Actual returns may vary based on market conditions. CAGR = Compound Annual Growth Rate.</p>
          </div>
        </div>
      </section>

      {/* Investment Strategy Section */}
      <div className={styles.section}>
        <h2>Investment Strategy</h2>
        <div className={styles.strategyContent}>
          {recommendations.explanation ? (
            typeof recommendations.explanation === 'string' ? (
              recommendations.explanation.split('\n').map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))
            ) : (
              <p>{JSON.stringify(recommendations.explanation)}</p>
            )
          ) : (
            <p>No strategy details available.</p>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className={styles.actionButtons}>
        <div className={styles.actionButtonGroup}>
          <button 
            onClick={generateNewRecommendations} 
            className={`${styles.button} ${generating ? styles.loading : ''}`}
            disabled={generating}
          >
            {generating ? 'Generating...' : 'Generate New Recommendations'}
          </button>
          <button 
            className={styles.secondaryButton}
            onClick={fetchRecommendations}
            disabled={loading}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        
        <div className={styles.actionButtonGroup}>
          <button 
            className={styles.primaryButton}
            onClick={handleSavePlan}
          >
            <DownloadIcon style={{ marginRight: '8px' }} />
            Download Full Report
          </button>
          <button 
            className={styles.secondaryButton}
            onClick={handleContactAdvisor}
          >
            <EmailIcon style={{ marginRight: '8px' }} />
            Get Personalized Advice
          </button>
        </div>
        
        <div className={styles.actionNote}>
          <p>Your plan updates automatically as market conditions change.</p>
          {lastUpdated && (
            <p className={styles.lastUpdated}>
              Last updated: {lastUpdated}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;