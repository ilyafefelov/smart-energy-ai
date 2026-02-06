"""
Ukrainian State Statistics Electricity Price Analyzer
Аналізатор цін на електроенергію з Державної служби статистики України

MLOps Integration: Transforms government statistical data into ML-ready features
for price forecasting and trend analysis in energy arbitrage system.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class UkraineElectricityPriceAnalyzer:
    """
    Analyzer for Ukrainian State Statistics electricity price data
    Transforms semi-annual statistical data into ML features
    """
    
    def __init__(self, csv_file_path: str):
        """
        Initialize analyzer with state statistics data
        
        Args:
            csv_file_path: Path to downloaded CSV from stat.gov.ua
        """
        self.csv_path = csv_file_path
        self.raw_data = None
        self.electricity_data = None
        self.processed_data = None
        
    def load_and_process_data(self) -> Dict:
        """Load and process the state statistics data"""
        
        logger.info(f"📊 Loading Ukrainian state statistics from {self.csv_path}")
        
        # Load raw data
        self.raw_data = pd.read_csv(self.csv_path)
        
        # Filter electricity data
        self.electricity_data = self.raw_data[self.raw_data['Тип палива/енергії'] == 'ELECTR'].copy()
        
        logger.info(f"⚡ Found {len(self.electricity_data)} electricity records")
        
        # Process the data
        processed = self._process_electricity_data()
        
        return {
            'total_records': len(self.raw_data),
            'electricity_records': len(self.electricity_data),
            'processed_records': len(processed),
            'date_range': f"{processed['period'].min()} - {processed['period'].max()}",
            'indicators': list(processed['indicator'].unique()),
            'consumer_types': list(processed['consumer_type'].unique())
        }
    
    def _process_electricity_data(self) -> pd.DataFrame:
        """Process electricity data into ML-ready format"""
        
        processed_records = []
        
        for _, row in self.electricity_data.iterrows():
            
            # Parse period (2018-S1 -> 2018, semester 1)
            period = row['Період']
            year = int(period.split('-')[0])
            semester = int(period.split('-S')[1])
            
            # Convert semester to approximate month (S1=June, S2=December)
            month = 6 if semester == 1 else 12
            date = datetime(year, month, 15)  # Mid-month
            
            # Parse indicator
            indicator_code = row['Показник']
            indicator_name = row['Показник.1']
            
            # Parse consumer type
            consumer_code = row['Тип споживача']
            consumer_name = row['Тип споживача.1']
            
            # Parse value
            value = row['Значення cпостереження']
            try:
                value = float(str(value).replace(',', '.'))
            except:
                continue  # Skip invalid values
            
            processed_records.append({
                'period': period,
                'date': date,
                'year': year,
                'semester': semester,
                'indicator': indicator_code,
                'indicator_name': indicator_name,
                'consumer_type': consumer_code,
                'consumer_name': consumer_name,
                'value': value,
                'unit': self._extract_unit(indicator_name)
            })
        
        self.processed_data = pd.DataFrame(processed_records)
        return self.processed_data
    
    def _extract_unit(self, indicator_name: str) -> str:
        """Extract unit from indicator name"""
        if 'грн за 1 кВт·год' in indicator_name:
            return 'UAH/kWh'
        elif 'грн' in indicator_name:
            return 'UAH'
        elif 'кВт·год' in indicator_name:
            return 'kWh'
        else:
            return 'unknown'
    
    def get_price_trends(self) -> Dict:
        """Analyze electricity price trends"""
        
        if self.processed_data is None:
            self.load_and_process_data()
        
        # Filter price data only
        price_data = self.processed_data[
            self.processed_data['indicator'].str.contains('PRICE', na=False)
        ].copy()
        
        if len(price_data) == 0:
            return {'error': 'No price data found'}
        
        # Group by consumer type and period
        trends = {}
        
        for consumer_type in price_data['consumer_type'].unique():
            consumer_data = price_data[price_data['consumer_type'] == consumer_type]
            
            # Sort by date
            consumer_data = consumer_data.sort_values('date')
            
            trends[consumer_type] = {
                'periods': consumer_data['period'].tolist(),
                'dates': consumer_data['date'].tolist(),
                'values': consumer_data['value'].tolist(),
                'consumer_name': consumer_data['consumer_name'].iloc[0] if len(consumer_data) > 0 else '',
                'unit': consumer_data['unit'].iloc[0] if len(consumer_data) > 0 else '',
                'trend_analysis': self._calculate_trend(consumer_data['value'].tolist())
            }
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> Dict:
        """Calculate trend statistics"""
        if len(values) < 2:
            return {}
        
        values = np.array(values)
        
        # Calculate percentage changes
        pct_changes = np.diff(values) / values[:-1] * 100
        
        return {
            'start_value': float(values[0]),
            'end_value': float(values[-1]),
            'total_change_pct': float((values[-1] - values[0]) / values[0] * 100),
            'average_value': float(np.mean(values)),
            'volatility': float(np.std(pct_changes)),
            'max_value': float(np.max(values)),
            'min_value': float(np.min(values)),
            'periods': len(values)
        }
    
    def create_ml_features(self) -> pd.DataFrame:
        """
        Create ML-ready features from state statistics data
        For integration with hybrid forecasting system
        """
        
        if self.processed_data is None:
            self.load_and_process_data()
        
        # Focus on price data for ML
        price_data = self.processed_data[
            self.processed_data['indicator'] == 'AVG_ELECTR_PRICE_WO_VAT'
        ].copy()
        
        # Create features
        ml_features = []
        
        for consumer_type in price_data['consumer_type'].unique():
            consumer_data = price_data[
                price_data['consumer_type'] == consumer_type
            ].sort_values('date')
            
            for i, row in consumer_data.iterrows():
                
                # Base features
                features = {
                    'date': row['date'],
                    'year': row['year'],
                    'semester': row['semester'],
                    'consumer_type': consumer_type,
                    'price_uah_kwh': row['value'],
                    'price_eur_kwh': row['value'] / 40.0,  # Approximate EUR conversion
                }
                
                # Time-based features
                features['year_normalized'] = (row['year'] - 2018) / (2024 - 2018)
                features['semester_sin'] = np.sin(2 * np.pi * row['semester'] / 2)
                features['semester_cos'] = np.cos(2 * np.pi * row['semester'] / 2)
                
                # Historical features (if available)
                if len(consumer_data) > 1:
                    consumer_values = consumer_data['value'].tolist()
                    current_idx = list(consumer_data.index).index(i)
                    
                    if current_idx > 0:
                        features['price_lag1'] = consumer_values[current_idx - 1]
                        features['price_change_pct'] = ((row['value'] - consumer_values[current_idx - 1]) / 
                                                       consumer_values[current_idx - 1] * 100)
                    
                    if current_idx >= 2:
                        features['price_lag2'] = consumer_values[current_idx - 2]
                        features['price_rolling_mean_3'] = np.mean(consumer_values[max(0, current_idx-2):current_idx+1])
                
                ml_features.append(features)
        
        ml_df = pd.DataFrame(ml_features)
        
        logger.info(f"🤖 Created ML features: {len(ml_df)} records, {len(ml_df.columns)} features")
        
        return ml_df
    
    def generate_report(self) -> str:
        """Generate comprehensive analysis report"""
        
        summary = self.load_and_process_data()
        trends = self.get_price_trends()
        
        report = []
        report.append("=" * 80)
        report.append("АНАЛІЗ ДЕРЖАВНОЇ СТАТИСТИКИ ЦІН НА ЕЛЕКТРОЕНЕРГІЮ")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append(f"📊 ЗАГАЛЬНА ІНФОРМАЦІЯ:")
        report.append(f"   Всього записів: {summary['total_records']}")
        report.append(f"   Записи по електроенергії: {summary['electricity_records']}")
        report.append(f"   Оброблено записів: {summary['processed_records']}")
        report.append(f"   Період даних: {summary['date_range']}")
        report.append("")
        
        # Indicators
        report.append(f"📋 ПОКАЗНИКИ:")
        for indicator in summary['indicators']:
            count = len(self.processed_data[self.processed_data['indicator'] == indicator])
            report.append(f"   {indicator}: {count} записів")
        report.append("")
        
        # Price trends
        report.append(f"💰 АНАЛІЗ ЦІНОВИХ ТРЕНДІВ:")
        report.append("")
        
        for consumer_type, trend_data in trends.items():
            if 'trend_analysis' in trend_data:
                analysis = trend_data['trend_analysis']
                consumer_name = trend_data['consumer_name']
                unit = trend_data['unit']
                
                report.append(f"👥 {consumer_name}:")
                report.append(f"   Початкова ціна: {analysis['start_value']:.2f} {unit}")
                report.append(f"   Кінцева ціна: {analysis['end_value']:.2f} {unit}")
                report.append(f"   Зміна: {analysis['total_change_pct']:+.1f}%")
                report.append(f"   Середня ціна: {analysis['average_value']:.2f} {unit}")
                report.append(f"   Волатильність: {analysis['volatility']:.1f}%")
                report.append(f"   Діапазон: {analysis['min_value']:.2f} - {analysis['max_value']:.2f} {unit}")
                report.append("")
        
        # ML integration potential
        ml_features = self.create_ml_features()
        report.append(f"🤖 ПОТЕНЦІАЛ ДЛЯ ML:")
        report.append(f"   ML-готових записів: {len(ml_features)}")
        report.append(f"   Фічерів для тренування: {len(ml_features.columns)}")
        report.append(f"   Можливість прогнозування: ⚠️ ОБМЕЖЕНА (піврічні дані)")
        report.append(f"   Рекомендація: Використовувати для довгострокового тренду")
        report.append("")
        
        return "\n".join(report)


def analyze_ukrainian_electricity_data(csv_path: str) -> Dict:
    """
    Main function to analyze Ukrainian electricity price data
    
    Args:
        csv_path: Path to downloaded CSV from stat.gov.ua
        
    Returns:
        Analysis results dictionary
    """
    
    analyzer = UkraineElectricityPriceAnalyzer(csv_path)
    
    # Generate comprehensive analysis
    summary = analyzer.load_and_process_data()
    trends = analyzer.get_price_trends()
    ml_features = analyzer.create_ml_features()
    report = analyzer.generate_report()
    
    # Print report
    print(report)
    
    return {
        'summary': summary,
        'trends': trends,
        'ml_features': ml_features,
        'analyzer': analyzer,
        'recommendations': {
            'data_quality': 'HIGH - Official government statistics',
            'frequency': 'LOW - Semi-annual data only',
            'ml_suitability': 'MODERATE - Good for long-term trends',
            'integration_potential': 'HIGH - Can enhance OREE real-time data',
            'action_needed': 'Combine with daily OREE data for complete picture'
        }
    }


if __name__ == "__main__":
    # Test with the downloaded file
    csv_file = "data/raw/dataset_2026-02-06T17_04_21.420998765Z_DEFAULT_INTEGRATION_SSSU_DF_CONSUMER_PRICES_FOR_NATURAL_GAS_AND_ELECTRICITY_LATEST.csv"
    
    print("🔍 АНАЛІЗ ДЕРЖАВНОЇ СТАТИСТИКИ УКРАЇНИ")
    print("=" * 60)
    
    try:
        results = analyze_ukrainian_electricity_data(csv_file)
        
        print("\n🎯 ВИСНОВКИ:")
        print(f"✅ Аналіз завершено успішно")
        print(f"📊 Якість даних: {results['recommendations']['data_quality']}")
        print(f"📅 Частота даних: {results['recommendations']['frequency']}")
        print(f"🤖 ML придатність: {results['recommendations']['ml_suitability']}")
        print(f"🔄 Інтеграція: {results['recommendations']['integration_potential']}")
        print(f"\n💡 Дії: {results['recommendations']['action_needed']}")
        
    except Exception as e:
        print(f"❌ Помилка аналізу: {e}")
        import traceback
        traceback.print_exc()