import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: '2rem',
            margin: '1.5rem',
            borderRadius: '12px',
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#f87171',
            textAlign: 'center',
            maxWidth: 600,
            marginLeft: 'auto',
            marginRight: 'auto'
          }}
        >
          <AlertTriangle size={36} color="#ef4444" style={{ marginBottom: '1rem' }} />
          <h3 style={{ margin: '0 0 0.5rem', color: '#fff', fontSize: '1.1rem' }}>
            {this.props.title || 'Component Encountered an Issue'}
          </h3>
          <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '1rem' }}>
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            onClick={this.handleReset}
            style={{
              padding: '6px 16px',
              fontSize: '0.8rem',
              borderRadius: '6px',
              border: '1px solid #38bdf8',
              background: 'rgba(56, 189, 248, 0.2)',
              color: '#38bdf8',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontWeight: 600
            }}
          >
            <RefreshCw size={14} />
            <span>Reset Component</span>
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
