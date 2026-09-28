import React from 'react';
import { Severity, RiskLevel, FindingCategory } from '../types';

interface StatusBadgeProps {
  type: 'severity' | 'risk' | 'category' | 'status';
  value: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value }) => {
  const cleanVal = (value || '').toUpperCase();

  if (type === 'severity' || type === 'risk') {
    switch (cleanVal) {
      case 'CRITICAL':
        return <span className="badge badge-critical">{cleanVal}</span>;
      case 'HIGH':
        return <span className="badge badge-high">{cleanVal}</span>;
      case 'MODERATE':
      case 'MEDIUM':
        return <span className="badge badge-moderate">{cleanVal}</span>;
      case 'LOW':
      case 'INFORMATIONAL':
        return <span className="badge badge-low">{cleanVal}</span>;
      default:
        return <span className="badge">{cleanVal}</span>;
    }
  }

  if (type === 'category') {
    if (cleanVal === 'EXECUTION_GAP') {
      return <span className="badge badge-gap">EXECUTION GAP</span>;
    }
    if (cleanVal === 'NEGATIVE_SPACE') {
      return <span className="badge badge-negative">NEGATIVE SPACE</span>;
    }
    return <span className="badge">{cleanVal}</span>;
  }

  // General status
  if (['RESOLVED', 'REVIEWED', 'VERIFIED', 'COMPLETED', 'SUCCESS'].includes(cleanVal)) {
    return <span className="badge badge-low">{cleanVal}</span>;
  }
  if (['OPEN', 'PENDING', 'RUNNING'].includes(cleanVal)) {
    return <span className="badge badge-high">{cleanVal}</span>;
  }
  if (['FAILED', 'CRITICAL'].includes(cleanVal)) {
    return <span className="badge badge-critical">{cleanVal}</span>;
  }

  return <span className="badge">{cleanVal}</span>;
};
