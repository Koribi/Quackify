import spotipy
from spotipy.oauth2 import SpotifyOAuth
import spotipy.util as util
import spotify_uri
import time
import discord
from discord.ext import commands
from discord.utils import get
import wavelink
from config import *


class Quackify:
	discord_channels = dict() 
	spotify_playlists = dict()
	spotify_user = None

	def __init__(self, ctx : discord.Client, spoti : spotipy.Spotify):
		self.ctx = ctx
		self.spoti = spoti

	
	#On start
	async def run(self):
		

		discord_channels = self.__get_discord_channels()
		self.discord_channels = discord_channels

		spotify_playlists = self.__get_spotify_playlists(discord_channels.keys())
		self.spotify_playlists = spotify_playlists

		self.spotify_user = self.__get_current_spotify_user()
		
		if self.__create_missing_spotify_playlists(self.spotify_user, 
											   discord_channels.keys(), 
											   spotify_playlists):
			spotify_playlists = self.__get_spotify_playlists(discord_channels.keys())

		print(spotify_playlists)

		


		for channel_name, channel_id in discord_channels.items():
			spotify_playlist = spotify_playlists[channel_name]

			messages = await self.get_all_messages(channel_id)

			messages = await self.__clear_duplicate_discord_messages(messages)

			self.__add_spotify_songs(messages, spotify_playlist)

			if self.__clear_playlist_on_mismatch(messages, spotify_playlist):
				self.__add_spotify_songs(messages, spotify_playlist)



	## Discord methods
	
	#Get all discord channels in specified category
	def __get_discord_channels(self):
		result = dict()
		for guild in self.ctx.guilds:
			for channel in guild.channels:
				if channel.category_id == 952568175134920724:
					result[channel.name] = channel.id
					

					
		return result

	#Get all messages in channel
	async def get_all_messages(self, discord_channel_id):
		messages = self.ctx.get_channel(discord_channel_id)
		return await messages.history(limit=None, oldest_first=True).flatten()

	#Get order of songs in channel
	def __get_discord_song_order(self, discord_messages):
		result = list()

		for message in discord_messages:
			if 'https://open.spotify.com/track/' in message.content:
				result.append(spotify_uri.parse(message.content).id)
		return result

	#Delete duplicate messages in discord channel
	async def __clear_duplicate_discord_messages(self, discord_messages):
		added_messages = list()
		updated_messages = list()

		for message in discord_messages:
			if 'https://open.spotify.com/track/' in message.content:
				if spotify_uri.parse(message.content).id in added_messages:
					await message.delete()
					print('DELETED')
					
				else:
					added_messages.append(spotify_uri.parse(message.content).id)
					updated_messages.append(message)
		return updated_messages
		
	#On new message in Discord
	async def song_add(self, message):

		if 'https://open.spotify.com/track/' in message.content:
			self.__add_spotify_songs([message], self.spotify_playlists[message.channel.name])

	#New channel creation
	async def new_channel_creation(self, channel):
		if channel.category_id == 952568175134920724:
			self.__create_missing_spotify_playlists(sesh.spotify_user, 
											   	   {channel.name:channel.id}, 
											   	   sesh.spotify_playlists)
		sesh.discord_channels = self.__get_discord_channels()
		sesh.spotify_playlists = self.__get_spotify_playlists(sesh.discord_channels)
	
	#Channel renaming
	async def channel_rename(self, old_channel, new_channel):
		if old_channel.category_id == 952568175134920724:
			if old_channel.name != new_channel.name:
				sesh.discord_channels = self.__get_discord_channels()
				self.spoti.playlist_change_details(sesh.spotify_playlists[old_channel.name],
												   self.formatting(new_channel.name))
				sesh.spotify_playlists = self.__get_spotify_playlists(sesh.discord_channels)

	#On channel deletion delete playlist
	async def channel_delete(self, channel):
		if channel.category_id == 952568175134920724:
			sesh.discord_channels = self.__get_discord_channels()
			self.spoti.current_user_unfollow_playlist(sesh.spotify_playlists[channel.name])
			sesh.spotify_playlists = self.__get_spotify_playlists(sesh.discord_channels)

	#On message deletion delete song in playlist
	async def song_delete(self, payload):
		if payload.channel_id in sesh.discord_channels.values():
			channel_name_from_id = dict((v,k) for k,v in sesh.discord_channels.items())
			messages = await self.get_all_messages(payload.channel_id)

			#self.__clear_spotify_playlist(sesh.spotify_playlists[channel_name_from_id[payload.channel_id]])					
			#self.__add_spotify_songs(messages, sesh.spotify_playlists[channel_name_from_id[payload.channel_id]])

			#LINUS GE ÅSIKT
			songs_id = list()
			for message in messages:
				if 'https://open.spotify.com/track/' in message.content:
					songs_id.append(spotify_uri.parse(message.content).id)

			playlist_songs = sesh.__get_spotify_playlist_songs(sesh.spotify_playlists[channel_name_from_id[payload.channel_id]])			
			song_to_remove = [song for song in playlist_songs if song not in songs_id]
			sesh.spoti.playlist_remove_all_occurrences_of_items(
																sesh.spotify_playlists[channel_name_from_id[payload.channel_id]],
																song_to_remove)




	## Spotify methods

	#Get spotify playlists
	def __get_spotify_playlists(self, discord_channels):
		'''Extract spotify channels with the same name as discord channels'''
		result = dict()
		offset = 0

		
		# Run until we have looked through all of the playlists of user
		while True:
			request = self.spoti.current_user_playlists(offset=offset)
			items = request['items']
			for item in items:
				# Match discord channels and spotify playlists
				if self.reverse_formatting(item['name']) in discord_channels:
					result[self.reverse_formatting(item['name'])] = item['id']

			offset += len(items)

			# If we ran out of playlists to look at, break loop
			if offset + 1 > request['total']:
				break

		return result

	#Get spotify user
	def __get_current_spotify_user(self):
		return self.spoti.current_user()['id']

	#Create missing spotify playlists
	def __create_missing_spotify_playlists(self,
										  spotify_user,
										  discord_channels, 
										  spotify_playlists):

		new_playlists = False
		# LINUS ONE LINER AAAAAAAAAAAAAAAAAAAA
		uncreated_playlists = [item for item in discord_channels if item not in spotify_playlists]
		
		for item in uncreated_playlists:
			self.spoti.user_playlist_create(user=spotify_user,
									   name=self.formatting(item),
									   description='')
			new_playlists = True
		return new_playlists

	#Get all songs in playlist
	def __get_spotify_playlist_songs(self, playlist_id):
		'''Gets spotify playlist songs from provided ID'''
		tracks = []
		offset = 0

		while True:
			request = self.spoti.playlist_tracks(playlist_id=playlist_id,
										fields=None,
										offset=offset)
			items = request['items']
			for item in items:
				tracks.append(item['track']['id'])

			offset += len(items)

			# If we ran out of playlists to look at, break loop
			if offset + 1 > request['total']:
				break

		return tracks

	#Add new songs to playlist
	def __add_spotify_songs(self, 
							discord_messages,  
							spotify_playlist):
		spotify_songs = self.__get_spotify_playlist_songs(spotify_playlist)
		for message in discord_messages:
			if 'https://open.spotify.com/track/' in message.content:
				if spotify_uri.parse(message.content).id not in spotify_songs:
					self.spoti.playlist_add_items(spotify_playlist, {message.content})

	#Checks if playlist is the same as channel
	def __clear_playlist_on_mismatch(self, discord_messages, spotify_playlist):
		discord_song_order = self.__get_discord_song_order(discord_messages)
		spotify_song_order = self.__get_spotify_playlist_songs(spotify_playlist)
		
		if len(discord_song_order) != len(spotify_song_order):
			self.__clear_spotify_playlist(spotify_playlist)
			return True

		index = 0
		for song in discord_song_order:
			if spotify_song_order[index] != song:
				self.__clear_spotify_playlist(spotify_playlist)
				return True
			index += 1

		return False

	#Clears playlist
	def __clear_spotify_playlist(self, spotify_playlist):

		spotify_songs = self.__get_spotify_playlist_songs(spotify_playlist)
		self.spoti.playlist_remove_all_occurrences_of_items(spotify_playlist, spotify_songs)

		

	##Other methods

	#Capitalize and remove dashes
	def formatting(self, text):
		return_text = text.capitalize().replace('-', ' ')
		return return_text

	#Lowercase and remove spaces
	def reverse_formatting(self, text):
		return_text = text.lower().replace(' ', '-')
		return return_text

	##Voice methods
	
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


'''  Below code sets up a discord client for the bot and the spotify session '''

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(username='koribi',
									   scope='playlist-modify-private streaming playlist-modify-public',
									   client_id=SPOTIFY_CLIENT_ID,
									   client_secret=SPOTIFY_CLIENT_SECRET,
									   redirect_uri='http://localhost:8888/callback/'))

	
#token = util.prompt_for_user_token(username='koribi',
#									   scope='playlist-modify-private',
#									   client_id='01a658181c7c4e32a4594296715e4c6d',
#									   client_secret='be7f153635144606916c6f8dafbd7f66',
#									   redirect_uri='http://localhost:8888/callback/')

#sp = spotipy.Spotify(auth=token)
bot = commands.Bot(command_prefix='.')

sesh = Quackify(bot, sp)


@bot.event
async def on_ready():
	''' This function is called when the discord bot has set everything up.'''

	await sesh.run()
	bot.loop.create_task(node_connect())
	print('Bot started')

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
	print(f'Node {node.identifier} is ready')

#Wavelink connect
async def node_connect():
	await bot.wait_until_ready()
	await wavelink.NodePool.create_node(bot=bot,
									    host='www.lavalinknodepublic2.ml',
										port=443,
										password='mrextinctcodes',
										https=True)

##Bot commands

#Play
@bot.command()
async def play(ctx, *, search: wavelink.YouTubeTrack):
	if not ctx.voice_client:
		vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
	elif not ctx.author.voice_client:
		return await ctx.reply("You're not connected to a voice channel")
	else:
		vc : wavelink.Player = ctx.voice_client

	await vc.play(search)

	



@bot.event
async def on_message(message):
	''' This function is called every time we get a message. '''

	#Adds new song to correct playlist
	await sesh.song_add(message)

	await bot.process_commands(message)


@bot.event
async def on_guild_channel_create(channel):

	#Create new playlist on new channel creation
	await sesh.new_channel_creation(channel)

	

@bot.event
async def on_guild_channel_update(old_channel, new_channel):

	#Create new playlist on new channel creation
	await sesh.channel_rename(old_channel, new_channel)

@bot.event
async def on_guild_channel_delete(channel):

	#Create new playlist on new channel creation
	await sesh.channel_delete(channel)

@bot.event
async def on_raw_message_delete(payload):
	print('Message deleted')
	await sesh.song_delete(payload)


# Start discord client for bot X
bot.run(DISCORD_TOKEN)