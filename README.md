# Cryptocurrency Trading Bot - SMA Crossover Strategy

A Python-based cryptocurrency trading bot that implements a Simple Moving Average (SMA) crossover strategy for automated trading on Coinbase Pro.

## 🚀 Features

- **SMA Crossover Strategy**: Uses 5-period and 20-period Simple Moving Averages
- **Multi-Pair Monitoring**: Monitors all available USD trading pairs on Coinbase Pro
- **Dry Run Mode**: Safe simulation mode enabled by default
- **Real-time Analysis**: Continuous market monitoring with configurable intervals
- **Error Handling**: Robust error handling for network and API failures
- **Rate Limiting**: Built-in rate limiting to comply with exchange limits

## 📋 Requirements

- Python 3.10 or higher
- Coinbase Pro account (for live trading)
- API credentials (for live trading)

## 🛠️ Installation

1. **Install Dependencies**:
   The following packages will be automatically installed:
   - ccxt (cryptocurrency exchange integration)
   - python-dotenv (environment variable management)
   - requests (HTTP requests)

2. **Configure Environment Variables**:
   - Copy `.env.example` to `.env`
   - Add your Coinbase Pro API credentials (only needed for live trading)

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with your API credentials:

```env
COINBASE_API_KEY=your_api_key_here
COINBASE_API_SECRET=your_api_secret_here
COINBASE_API_PASSPHRASE=your_api_passphrase_here
