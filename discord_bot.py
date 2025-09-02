import os
import discord
import requests
import asyncio
import threading
from datetime import datetime, timedelta
from discord.ext import commands
from flask import Flask, jsonify

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration
FLASK_SERVER_URL = os.environ.get('FLASK_SERVER_URL', 'http://localhost:5000')
COMMISSION_CHANNEL_ID = int(os.environ.get("COMMISSION_CHANNEL_ID", "0"))
GUILD_ID = int(os.environ.get("GUILD_ID", "0"))
ADMIN_ROLE_NAME = os.environ.get("ADMIN_ROLE_NAME", "Admin")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='commission')
async def create_commission(ctx, commission_type=None, *, skills=None):
    """Create a new commission request"""
    if not commission_type or not skills:
        embed = discord.Embed(
            title="Commission Creation",
            description="Usage: `!commission <type> <skills>`\n\n"
                       "**Types:**\n"
                       "• `merc` - Merc for Hire\n"
                       "• `team` - Merc Team for Hire\n"
                       "• `task` - Task for a Merc Team\n\n"
                       "**Example:** `!commission merc Python, Web Development, API Integration`",
            color=0x7289DA
        )
        await ctx.send(embed=embed)
        return

    valid_types = {
        'merc': 'Merc for Hire',
        'team': 'Merc Team for Hire', 
        'task': 'Task for a Merc Team'
    }

    if commission_type not in valid_types:
        await ctx.send("❌ Invalid commission type. Use: `merc`, `team`, or `task`")
        return

    # Call Flask API to create commission
    try:
        print(f"Connecting to Flask server at: {FLASK_SERVER_URL}")
        
        # Test if Flask server is reachable
        health_response = requests.get(f'{FLASK_SERVER_URL}/', timeout=10)
        if health_response.status_code != 200:
            await ctx.send("❌ Commission system is currently offline. Please try again later.")
            return
        
        response = requests.post(f'{FLASK_SERVER_URL}/api/commissions', 
            json={
                'discord_id': str(ctx.author.id),
                'username': ctx.author.name,
                'display_name': ctx.author.display_name,
                'commission_type': valid_types[commission_type],
                'skills': skills.strip()
            },
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"API Response Status: {response.status_code}")
        print(f"API Response Text: {response.text}")
        
        if response.status_code == 201:
            data = response.json()
            embed = discord.Embed(
                title="✅ Commission Submitted",
                description=f"Your **{valid_types[commission_type]}** request has been submitted for admin approval.\n\n"
                           f"**Skills:** {skills}\n"
                           f"**Commission ID:** #{data['commission_id']}\n\n"
                           f"You'll receive a DM when your commission is approved or if there are any updates.",
                color=0x00FF00
            )
            try:
                await ctx.author.send(embed=embed)
                await ctx.send(f"✅ Commission submitted! Check your DMs for confirmation.")
            except discord.Forbidden:
                await ctx.send(embed=embed)
        else:
            try:
                error_data = response.json()
                error_msg = f"❌ {error_data.get('error', 'Unknown error occurred')}"
            except:
                error_msg = f"❌ Server error (Status: {response.status_code})"
            
            try:
                await ctx.author.send(error_msg)
                await ctx.send("❌ Commission creation failed. Check your DMs for details.")
            except discord.Forbidden:
                await ctx.send(error_msg)
            
    except requests.exceptions.ConnectionError:
        await ctx.send("❌ Cannot connect to commission system. Please check server status.")
    except requests.exceptions.Timeout:
        await ctx.send("❌ Commission system timeout. Please try again later.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        await ctx.send(f"❌ Error connecting to commission system. Please contact admin.")

@bot.command(name='accept')
async def accept_commission(ctx, commission_id: int):
    """Accept a commission"""
    try:
        response = requests.post(f'{FLASK_SERVER_URL}/api/commissions/{commission_id}/accept', json={
            'discord_id': str(ctx.author.id),
            'username': ctx.author.name,
            'display_name': ctx.author.display_name
        })
        
        if response.status_code == 200:
            data = response.json()
            embed = discord.Embed(
                title="🤝 Commission Accepted",
                description=f"Commission #{commission_id} has been accepted!\n\n"
                           f"Please coordinate with the commission creator.\n"
                           f"You can now discuss project details and timeline.",
                color=0x00FF00
            )
            try:
                await ctx.author.send(embed=embed)
                await ctx.send(f"✅ Commission #{commission_id} accepted! Check your DMs for details.")
            except discord.Forbidden:
                await ctx.send(embed=embed)
        else:
            error_data = response.json()
            error_msg = f"❌ {error_data.get('error', 'Unknown error occurred')}"
            try:
                await ctx.author.send(error_msg)
                await ctx.send("❌ Commission acceptance failed. Check your DMs for details.")
            except discord.Forbidden:
                await ctx.send(error_msg)
            
    except Exception as e:
        await ctx.send(f"❌ Error connecting to commission system: {e}")

@bot.command(name='help_commission')
async def help_commission(ctx):
    """Show help for commission commands"""
    embed = discord.Embed(
        title="🔧 Commission Bot Commands",
        description="Commands for managing mercenary commissions",
        color=0x7289DA
    )
    
    embed.add_field(
        name="📝 Create Commission",
        value="`!commission <type> <skills>`\n"
              "Types: `merc`, `team`, `task`",
        inline=False
    )
    
    embed.add_field(
        name="🤝 Accept Commission",
        value="`!accept <commission_id>`\n"
              "Accept an approved commission",
        inline=False
    )
    
    embed.add_field(
        name="📋 Commission Types",
        value="• **merc** - Individual for hire\n"
              "• **team** - Team for hire\n"
              "• **task** - Task for a team",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Create Flask app for web service
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy", 
        "bot_status": "connected" if bot.is_ready() else "connecting",
        "timestamp": datetime.utcnow().isoformat()
    })

@web_app.route('/bot/status')
def bot_status():
    """Bot status endpoint"""
    return jsonify({
        "bot_ready": bot.is_ready(),
        "bot_user": str(bot.user) if bot.user else None,
        "guild_count": len(bot.guilds) if bot.is_ready() else 0
    })

def run_bot():
    """Run Discord bot in a separate thread"""
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    if not bot_token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set")
        return
    
    bot.run(bot_token)

def run_web_app():
    """Run Flask web app"""
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask web server on port {port}")
    web_app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    print("Starting Discord Commission Bot Service...")
    
    # Start Discord bot in background thread
    print("Starting Discord bot thread...")
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Give bot a moment to start
    import time
    time.sleep(2)
    
    # Run Flask web app (keeps the service alive)
    print("Starting Flask web server...")
    run_web_app()