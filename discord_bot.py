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

# Use discord.Bot for slash commands
bot = discord.Bot(command_prefix='!', intents=intents)

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

# Slash Commands
@bot.slash_command(name="help", description="Get help with commission bot commands")
async def help_slash(ctx):
    """Show help for commission commands"""
    embed = discord.Embed(
        title="🔧 Commission Bot Commands",
        description="Slash commands for managing mercenary commissions",
        color=0x7289DA
    )
    
    embed.add_field(
        name="👤 User Commands",
        value="`/submit` - Start commission submission\n"
              "`/mycommissions` - View your commissions\n"
              "`/mystats` - View your stats\n"
              "`/commission <id>` - View commission details\n"
              "`/complete <id>` - Mark commission complete\n"
              "`/report <id>` - Submit karma report\n"
              "`/leaderboard` - View karma rankings",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Admin Commands",
        value="`/pending` - List pending commissions\n"
              "`/approve <id>` - Approve commission\n"
              "`/reject <id>` - Reject commission\n"
              "`/reports` - View karma reports\n"
              "`/set_admin_channel` - Set admin channel\n"
              "`/set_public_channel` - Set public channel",
        inline=False
    )
    
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(name="submit", description="Start commission submission process via DM")
async def submit_slash(ctx):
    """Start commission submission process via DM"""
    try:
        embed = discord.Embed(
            title="📝 Commission Submission",
            description="Let's create your commission request!\n\n"
                       "Use the following format:\n"
                       "`!commission <type> <skills>`\n\n"
                       "**Types:**\n"
                       "• `merc` - Merc for Hire\n"
                       "• `team` - Merc Team for Hire\n"
                       "• `task` - Task for a Merc Team\n\n"
                       "**Example:**\n"
                       "`!commission merc Python, Web Development, API Integration`",
            color=0x7289DA
        )
        
        await ctx.user.send(embed=embed)
        await ctx.respond("✅ Check your DMs for commission submission instructions!", ephemeral=True)
    except discord.Forbidden:
        await ctx.respond("❌ I couldn't send you a DM. Please enable DMs from server members.", ephemeral=True)

@bot.slash_command(name="mycommissions", description="View your commission history")
async def mycommissions_slash(ctx):
    """View your commission history"""
    try:
        response = requests.get(f'{FLASK_SERVER_URL}/api/users/{ctx.user.id}/commissions', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            commissions = data.get('commissions', [])
            
            if not commissions:
                await ctx.respond("📋 You haven't created any commissions yet.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Your Commission History",
                description=f"Found {len(commissions)} commissions",
                color=0x7289DA
            )
            
            for comm in commissions[:10]:  # Show last 10
                status_emoji = {
                    'pending': '⏳',
                    'approved': '✅',
                    'rejected': '❌',
                    'accepted': '🤝',
                    'completed': '✅',
                    'expired': '⏰'
                }.get(comm['status'], '❓')
                
                embed.add_field(
                    name=f"{status_emoji} Commission #{comm['id']}",
                    value=f"**Type:** {comm['commission_type']}\n"
                          f"**Status:** {comm['status'].title()}\n"
                          f"**Skills:** {comm['skills'][:50]}{'...' if len(comm['skills']) > 50 else ''}",
                    inline=True
                )
            
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await ctx.respond("❌ Error fetching your commissions. Try again later.", ephemeral=True)
    except Exception as e:
        print(f"Error in mycommissions: {e}")
        await ctx.respond("❌ Connection error. Please try again later.", ephemeral=True)

@bot.slash_command(name="commission", description="View detailed information about a commission")
async def commission_slash(ctx, commission_id: int):
    """View detailed information about a commission"""
    try:
        response = requests.get(f'{FLASK_SERVER_URL}/api/commissions/{commission_id}', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            comm = data['commission']
            
            embed = discord.Embed(
                title=f"📋 Commission #{comm['id']}",
                description=f"**Type:** {comm['commission_type']}",
                color=0x7289DA
            )
            
            embed.add_field(name="Skills Required", value=comm['skills'], inline=False)
            embed.add_field(name="Status", value=comm['status'].title(), inline=True)
            embed.add_field(name="Creator", value=f"<@{comm['user']['discord_id']}>", inline=True)
            
            if comm.get('accepter'):
                embed.add_field(name="Accepter", value=f"<@{comm['accepter']['discord_id']}>", inline=True)
            
            embed.add_field(name="Created", value=comm['created_at'][:19], inline=True)
            
            if comm.get('expires_at'):
                embed.add_field(name="Expires", value=comm['expires_at'][:19], inline=True)
            
            await ctx.respond(embed=embed)
        else:
            await ctx.respond("❌ Commission not found.", ephemeral=True)
    except Exception as e:
        print(f"Error in commission: {e}")
        await ctx.respond("❌ Error fetching commission details.", ephemeral=True)

@bot.slash_command(name="complete", description="Mark a commission as completed")
async def complete_slash(ctx, commission_id: int, documentation: str = "No documentation provided"):
    """Mark a commission as completed"""
    try:
        response = requests.post(f'{FLASK_SERVER_URL}/api/commissions/{commission_id}/complete',
            json={
                'discord_id': str(ctx.user.id),
                'username': ctx.user.name,
                'documentation': documentation
            },
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            await ctx.respond(f"✅ {data['message']}", ephemeral=True)
        else:
            error_data = response.json()
            await ctx.respond(f"❌ {error_data.get('error', 'Unknown error')}", ephemeral=True)
    except Exception as e:
        print(f"Error in complete: {e}")
        await ctx.respond("❌ Error marking commission complete.", ephemeral=True)

@bot.slash_command(name="pending", description="List all pending commissions (Admin only)")
async def pending_slash(ctx):
    """List all pending commissions (Admin only)"""
    # Check if user has admin role
    if not any(role.name.lower() == ADMIN_ROLE_NAME.lower() for role in ctx.user.roles):
        await ctx.respond("❌ This command requires admin permissions.", ephemeral=True)
        return
    
    try:
        response = requests.get(f'{FLASK_SERVER_URL}/api/commissions/pending', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            commissions = data.get('commissions', [])
            
            if not commissions:
                await ctx.respond("📋 No pending commissions.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="⏳ Pending Commissions",
                description=f"Found {len(commissions)} pending approval",
                color=0xFFAA00
            )
            
            for comm in commissions[:10]:
                embed.add_field(
                    name=f"Commission #{comm['id']}",
                    value=f"**Type:** {comm['commission_type']}\n"
                          f"**Creator:** <@{comm['user']['discord_id']}>\n"
                          f"**Skills:** {comm['skills'][:100]}{'...' if len(comm['skills']) > 100 else ''}\n"
                          f"**Created:** {comm['created_at'][:19]}",
                    inline=False
                )
            
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await ctx.respond("❌ Error fetching pending commissions.", ephemeral=True)
    except Exception as e:
        print(f"Error in pending: {e}")
        await ctx.respond("❌ Connection error. Please try again later.", ephemeral=True)

@bot.slash_command(name="approve", description="Approve a pending commission (Admin only)")
async def approve_slash(ctx, commission_id: int):
    """Approve a pending commission (Admin only)"""
    # Check if user has admin role
    if not any(role.name.lower() == ADMIN_ROLE_NAME.lower() for role in ctx.user.roles):
        await ctx.respond("❌ This command requires admin permissions.", ephemeral=True)
        return
    
    try:
        response = requests.post(f'{FLASK_SERVER_URL}/api/commissions/{commission_id}/approve',
            json={'admin_id': str(ctx.user.id), 'admin_name': ctx.user.display_name},
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            await ctx.respond(f"✅ {data['message']}", ephemeral=True)
        else:
            error_data = response.json()
            await ctx.respond(f"❌ {error_data.get('error', 'Unknown error')}", ephemeral=True)
    except Exception as e:
        print(f"Error in approve: {e}")
        await ctx.respond("❌ Error approving commission.", ephemeral=True)

@bot.slash_command(name="reject", description="Reject a pending commission (Admin only)")
async def reject_slash(ctx, commission_id: int, reason: str = "No reason provided"):
    """Reject a pending commission (Admin only)"""
    # Check if user has admin role
    if not any(role.name.lower() == ADMIN_ROLE_NAME.lower() for role in ctx.user.roles):
        await ctx.respond("❌ This command requires admin permissions.", ephemeral=True)
        return
    
    try:
        response = requests.post(f'{FLASK_SERVER_URL}/api/commissions/{commission_id}/reject',
            json={'admin_id': str(ctx.user.id), 'reason': reason},
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            await ctx.respond(f"✅ {data['message']}", ephemeral=True)
        else:
            error_data = response.json()
            await ctx.respond(f"❌ {error_data.get('error', 'Unknown error')}", ephemeral=True)
    except Exception as e:
        print(f"Error in reject: {e}")
        await ctx.respond("❌ Error rejecting commission.", ephemeral=True)

@bot.slash_command(name="mystats", description="View your stats")
async def mystats_slash(ctx):
    """View your stats"""
    try:
        response = requests.get(f'{FLASK_SERVER_URL}/api/users/{ctx.user.id}/stats', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            stats = data['stats']
            
            embed = discord.Embed(
                title=f"📊 Stats for {ctx.user.display_name}",
                color=0x00FF00
            )
            
            embed.add_field(name="Total Commissions", value=stats.get('total_commissions', 0), inline=True)
            embed.add_field(name="Completed", value=stats.get('completed_commissions', 0), inline=True) 
            embed.add_field(name="Success Rate", value=f"{stats.get('success_rate', 0):.1f}%", inline=True)
            embed.add_field(name="Average Rating", value=f"{stats.get('average_rating', 0):.1f}/5", inline=True)
            embed.add_field(name="Karma Points", value=stats.get('karma_points', 0), inline=True)
            embed.add_field(name="Rank", value=f"#{stats.get('rank', 'N/A')}", inline=True)
            
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await ctx.respond("❌ Error fetching your stats.", ephemeral=True)
    except Exception as e:
        print(f"Error in mystats: {e}")
        await ctx.respond("❌ Connection error. Please try again later.", ephemeral=True)

@bot.slash_command(name="leaderboard", description="View the karma leaderboard")
async def leaderboard_slash(ctx):
    """View the karma leaderboard"""
    try:
        response = requests.get(f'{FLASK_SERVER_URL}/api/leaderboard', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            leaderboard = data.get('leaderboard', [])
            
            if not leaderboard:
                await ctx.respond("📊 No leaderboard data available yet.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🏆 Karma Leaderboard",
                description="Top mercenaries by karma points",
                color=0xFFD700
            )
            
            for i, user in enumerate(leaderboard[:10], 1):
                rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                embed.add_field(
                    name=f"{rank_emoji} {user['display_name'] or user['username']}",
                    value=f"**Karma:** {user['karma_points']}\n"
                          f"**Completed:** {user['completed_commissions']}\n"
                          f"**Rating:** {user['average_rating']:.1f}/5",
                    inline=True
                )
            
            await ctx.respond(embed=embed)
        else:
            await ctx.respond("❌ Error fetching leaderboard.", ephemeral=True)
    except Exception as e:
        print(f"Error in leaderboard: {e}")
        await ctx.respond("❌ Connection error. Please try again later.", ephemeral=True)

@bot.slash_command(name="report", description="Submit a karma report for a completed commission")
async def report_slash(ctx, commission_id: int, report_type: str, reason: str):
    """Submit a karma report for a completed commission"""
    if report_type.lower() not in ['positive', 'negative']:
        await ctx.respond("❌ Report type must be 'positive' or 'negative'.", ephemeral=True)
        return
    
    try:
        response = requests.post(f'{FLASK_SERVER_URL}/api/commissions/{commission_id}/report',
            json={
                'reporter_id': str(ctx.user.id),
                'reporter_name': ctx.user.display_name,
                'report_type': report_type.lower(),
                'reason': reason
            },
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            data = response.json()
            await ctx.respond(f"✅ {data['message']}", ephemeral=True)
        else:
            error_data = response.json()
            await ctx.respond(f"❌ {error_data.get('error', 'Unknown error')}", ephemeral=True)
    except Exception as e:
        print(f"Error in report: {e}")
        await ctx.respond("❌ Error submitting report.", ephemeral=True)

@bot.slash_command(name="reports", description="List pending karma reports (Admin only)")
async def reports_slash(ctx):
    """List pending karma reports (Admin only)"""
    # Check if user has admin role
    if not any(role.name.lower() == ADMIN_ROLE_NAME.lower() for role in ctx.user.roles):
        await ctx.respond("❌ This command requires admin permissions.", ephemeral=True)
        return
    
    try:
        response = requests.get(f'{FLASK_SERVER_URL}/api/reports/pending', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            reports = data.get('reports', [])
            
            if not reports:
                await ctx.respond("📋 No pending karma reports.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Pending Karma Reports",
                description=f"Found {len(reports)} pending reports",
                color=0xFFAA00
            )
            
            for report in reports[:10]:
                report_emoji = "👍" if report['report_type'] == 'positive' else "👎"
                embed.add_field(
                    name=f"{report_emoji} Report #{report['id']}",
                    value=f"**Commission:** #{report['commission_id']}\n"
                          f"**Reporter:** <@{report['reporter_id']}>\n"
                          f"**Type:** {report['report_type'].title()}\n"
                          f"**Reason:** {report['reason'][:100]}{'...' if len(report['reason']) > 100 else ''}",
                    inline=False
                )
            
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await ctx.respond("❌ Error fetching reports.", ephemeral=True)
    except Exception as e:
        print(f"Error in reports: {e}")
        await ctx.respond("❌ Connection error. Please try again later.", ephemeral=True)

@bot.slash_command(name="set_admin_channel", description="Set the admin approval channel (Admin only)")
async def set_admin_channel_slash(ctx, channel: discord.TextChannel):
    """Set the admin approval channel (Admin only)"""
    # Check if user has admin role
    if not any(role.name.lower() == ADMIN_ROLE_NAME.lower() for role in ctx.user.roles):
        await ctx.respond("❌ This command requires admin permissions.", ephemeral=True)
        return
    
    try:
        response = requests.post(f'{FLASK_SERVER_URL}/api/settings/admin_channel',
            json={'channel_id': str(channel.id), 'admin_id': str(ctx.user.id)},
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            await ctx.respond(f"✅ Admin approval channel set to {channel.mention}", ephemeral=True)
        else:
            await ctx.respond("❌ Error setting admin channel.", ephemeral=True)
    except Exception as e:
        print(f"Error in set_admin_channel: {e}")
        await ctx.respond("❌ Error setting admin channel.", ephemeral=True)

@bot.slash_command(name="set_public_channel", description="Set the public commission channel (Admin only)")
async def set_public_channel_slash(ctx, channel: discord.TextChannel):
    """Set the public commission channel (Admin only)"""
    # Check if user has admin role
    if not any(role.name.lower() == ADMIN_ROLE_NAME.lower() for role in ctx.user.roles):
        await ctx.respond("❌ This command requires admin permissions.", ephemeral=True)
        return
    
    try:
        response = requests.post(f'{FLASK_SERVER_URL}/api/settings/public_channel',
            json={'channel_id': str(channel.id), 'admin_id': str(ctx.user.id)},
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            await ctx.respond(f"✅ Public commission channel set to {channel.mention}", ephemeral=True)
        else:
            await ctx.respond("❌ Error setting public channel.", ephemeral=True)
    except Exception as e:
        print(f"Error in set_public_channel: {e}")
        await ctx.respond("❌ Error setting public channel.", ephemeral=True)

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