import discord
from discord.ext import commands
from discord.utils import get
import wavelink

class Music:

	def __init__(self, ctx : discord.Client, spoti : spotipy.Spotify):
		self.ctx = ctx
		self.spoti = spoti

	#Connect to voice
	async def connect_to_voice(self, ctx):
		bot_voice = ctx.guild.voice_client
		author_voice = ctx.author.voice
		voice = get(bot.voice_clients, guild=ctx.guild)

		if not author_voice: # Author not connected
			await ctx.send("You're not connected to a voice channel")

		elif ctx.bot.user in author_voice.channel.members: # Bot and Author both connected
			await ctx.send("**Already in the channel**")

		elif bot_voice and bot_voice.is_connected():# Connected but wrong channel
			await voice.move_to(ctx.author.voice.channel)
			await ctx.send("Moved to the voice channel")

		elif author_voice and not bot_voice: # Author connected but bot not connected
			voice_channel = await author_voice.channel.connect()
			await ctx.send("Connected to the voice channel")

