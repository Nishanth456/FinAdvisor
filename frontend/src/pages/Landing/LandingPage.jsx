import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import styles from './LandingPage.module.css';
import logo from '../../assets/logo.png';

const LandingPage = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className={styles.landing}>
      <header className={styles.header}>
        <nav className={styles.nav}>
          <div className={styles.logo}>FinAdvisor</div>
          <div className={styles.navLinks}>
            {isAuthenticated ? (
              <Link to="/dashboard" className={styles.navButton}>
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link to="/auth" className={styles.navLink}>
                  Login
                </Link>
                <Link to="/auth" className={styles.navButton}>
                  Get Started
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>

      <main className={styles.hero}>
        <div className={styles.heroContent}>
          <div>
            <h1>Smart Financial Planning with AI</h1>
            <p className={styles.subtitle}>
              Get personalized investment recommendations based on your financial goals and risk profile
            </p>
          </div>
          <div className={styles.ctaContainer}>
            <Link to="/auth" className={styles.ctaButton}>
              Start Your Financial Journey
            </Link>
          </div>
        </div>
        <div className={styles.heroImage}>
          <div className={styles.illustration}>
            <img src={logo} alt="FinAdvisor Logo" className={styles.logoImage} />
          </div>
        </div>
      </main>

      <section className={styles.features}>
        <h2>Why Choose FinAdvisor?</h2>
        <div className={styles.featuresGrid}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}></div>
            <h3>Personalized Recommendations</h3>
            <p>AI-powered investment suggestions tailored to your financial situation and goals.</p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}></div>
            <h3>Secure & Private</h3>
            <p>Your financial data is encrypted and never shared with third parties.</p>
          </div>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}></div>
            <h3>Performance Tracking</h3>
            <p>Monitor your investments and track progress toward your financial goals.</p>
          </div>
        </div>
      </section>

      <footer className={styles.footer}>
        <p>© 2025 FinAdvisor. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default LandingPage;