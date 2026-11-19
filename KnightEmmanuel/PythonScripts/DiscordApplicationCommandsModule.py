from LLMConfigsModule import *
from FileUtilitiesModule import *
from MainScanEngineModule import *
from ImageVideoGifPDFScanModule import *

# These values are updated by reset_user_uncensor_value_and_update_llm_usage.
ct = time.ctime(time.time()).split()
previousMonth = ct[1]
previousDate = ct[2]
previousYear = ct[4]

@Emmanuel.tree.command(
    name="emmanuel",
    description="Get Information about Knight Emmanuel."
)
async def emmanuel(ctx):
    await ctx.response.defer(ephemeral=True)
    await ctx.followup.send("I'm a knight designed by Sir David Nguyen with a purpose of scanning message, audio, "
                            "photo, gif, and video attachment in Server Channel that I am authorized to detect "
                            "inappropriate content using OpenAI LLMs, delete them, and annoy you with a DM warning"
                            " to stop sending NSFW content! I won't response to any Direct Messages!!!\n"
                            "If you like to delete DM messages from me, use the command /clear_emmanuel_dm_messages.\n"
                            "I have limitation to certain file formats that I am capable of scanning. The list can be checked "
                            "by the command /list_supported_file.")


@Emmanuel.tree.command(
    name="list_supported_file",
    description="Get a list of file formats Emmanuel can scan"
)
@app_commands.guild_only
async def list_supported_file(ctx):
    await ctx.response.defer(ephemeral=True)
    if ctx.guild.owner.id == ctx.user.id or ctx.user.id == OWNER_DISCORD_USER_ID:
        await ctx.followup.send(
            f"Image Formats: {SUPPORTED_PICTURE_FILE_FORMATS}\n"
            f"Video Formats: {SUPPORTED_VIDEO_FILE_FORMATS}\n"
            f"Audio Formats: {SUPPORTED_AUDIO_FILE_FORMATS}\n"
            f"Archive Formats: {SUPPORTED_ARCHIVE_FILE_FORMATS}\n"
            f"Disk Image Formats: {SUPPORTED_DISK_IMAGE_FORMATS}\n"
            f"ASCII-based file: {SUPPORTED_ASCII_READABLE_FILE_FORMATS}"
        )
    else:
        await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


@Emmanuel.tree.command(
    name="clear_emmanuel_dm_messages",
    description="Delete all direct messages sent by Knight Emmanuel to you"
)
async def clear_emmanuel_dm_messages(ctx):
    await ctx.response.defer(ephemeral=True)
    async for message in ctx.user.history():
        if message.author == Emmanuel.user:
            await message.delete()
    await ctx.followup.send("All DM messages by me have been deleted.")


@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=ZoneInfo("America/New_York")))  # A task every new day
async def reset_user_uncensor_value_and_update_llm_usage():
    global previousDate, previousMonth, previousYear

    print("\n")
    async with ConfigLock:
        for serverID in configuration:
            server = await Emmanuel.fetch_guild(int(serverID))
            for member in configuration[serverID]["User-Uncensor-Limit"]:
                configuration[serverID]["User-Uncensor-Limit"][member] = DAILY_UNCENSOR_LIMIT
            print(f"Resetting all members daily uncensor value in server {server.name} ID {server.id} - Status: SUCCESS")
        async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
            await file.write(json.dumps(configuration, indent=4))

    currentTime = time.ctime(time.time()).split()

    # Checking new date
    if currentTime[2] != previousDate:
        print(f"New Day of the Month Change: {previousMonth} {previousDate} -> {currentTime[1]} {currentTime[2]}")
        try:
            print(f"Updating LLMMonthlyUsageReport.png...")
            async with MonthlyCSVLock:
                monthlyData = await asyncio.to_thread(pd.read_csv, f"{LLM_USAGE_LOG}LLMMonthlyUsage.csv")
            monthlyTotalInputToken = []
            monthlyTotalOutputToken = []
            monthlyTotalCost = []
            for day in range(1, int(previousDate) + 1):
                dailyTotalInputToken = 0
                dailyTotalOutputToken = 0
                dailyTotalCost = 0
                for _, row in monthlyData.iterrows():
                    if int(row["Date"].split(" ")[1]) == day:
                        dailyTotalInputToken += row["Total Input Tokens"]
                        dailyTotalOutputToken += row["Total Output Tokens"]
                        dailyTotalCost += row["Total Cost"]
                monthlyTotalInputToken.append(dailyTotalInputToken)
                monthlyTotalOutputToken.append(dailyTotalOutputToken)
                monthlyTotalCost.append(round(dailyTotalCost, 5))
            datasets = [
                {"values": monthlyTotalInputToken, "title": "Total Input Tokens", "color": "Blue"},
                {"values": monthlyTotalOutputToken, "title": "Total Output Tokens", "color": "Green"},
                {"values": monthlyTotalCost, "title": "Total Cost ($)", "color": "Orange"},
            ]
            dates = [str(date) for date in range(1, int(previousDate) + 1)]
            plotBarCharts(datasets, dates, "LLM Usage - Monthly Overview",f"{LLM_USAGE_LOG}{previousYear}/{previousMonth}/LLMMonthlyUsageReport.png")
            print(f"Successfully Updating LLMMonthlyUsageReport.png!")
            try:
                print(f"Updating LLMModelsUsed.png...")
                LLMModels = []
                LLMModelUses = []
                for _, row in monthlyData.iterrows():
                    if row["LLM Models"] not in LLMModels:
                        LLMModels.append(row["LLM Models"])
                        LLMModelUses.append(1)
                    else:
                        LLMModelUses[LLMModels.index(row["LLM Models"])] += 1
                plotModelCalls(LLMModels, LLMModelUses, f"{LLM_USAGE_LOG}{previousYear}/{previousMonth}/LLMModelsUsed.png")
                print(f"Successfully Updating LLMModelsUsed.png!")
            except Exception as error:
                print(f"An error occurs while updating LLMModelsUsed.png\n{error}")

        except Exception as error:
            print(f"An error occurs while updating LLMMonthlyUsageReport.png\n{error}")

        previousDate = currentTime[2]

    # Checking new year
    if currentTime[4] != previousYear:
        print(f"New Year Change: {previousYear} -> {currentTime[4]}")
        try:
            print(f"Generating LLM Usage Yearly Report...")
            async with YearlyCSVLock:
                yearlyData = await asyncio.to_thread(pd.read_csv, f"{LLM_USAGE_LOG}LLMYearlyUsage.csv")
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            monthlyTotalInputTokens = []
            monthlyTotalOutputTokens = []
            monthlyTotalCosts = []
            for month in months:
                monthlyTotalInputToken = 0
                monthlyTotalOutputToken = 0
                monthlyTotalCost = 0
                for _, row in yearlyData.iterrows():
                    if row["Date"].split(' ')[0] == month:
                        monthlyTotalInputToken += row["Total Input Tokens"]
                        monthlyTotalOutputToken += row["Total Output Tokens"]
                        monthlyTotalCost += row["Total Cost"]
                monthlyTotalInputTokens.append(monthlyTotalInputToken)
                monthlyTotalOutputTokens.append(monthlyTotalOutputToken)
                monthlyTotalCosts.append(round(monthlyTotalCost, 5))
            datasets = [
                {"values": monthlyTotalInputTokens, "title": "Total Input Tokens", "color": "Blue"},
                {"values": monthlyTotalOutputTokens, "title": "Total Output Tokens", "color": "Green"},
                {"values": monthlyTotalCosts, "title": "Total Cost ($)", "color": "Orange"},
            ]
            plotBarCharts(datasets, months, "LLM Usage - End of Year Overview",f"{LLM_USAGE_LOG}{previousYear}/FullYearUsageReport.png")
            print(f"Successfully Generating LLM Usage Yearly Report!")

            try:
                print(f"Resetting LLMYearlyUsage.csv...")
                print(f"Successfully resetting LLMYearlyUsage.csv!")

                try:
                    print(f"Creating a new year folder...")
                    os.mkdir(f"{LLM_USAGE_LOG}{currentTime[4]}")
                    print(f"Successfully create a new year folder!")

                except Exception as error:
                    print(f"An error occurs while creating a new year folder\n{error}")

            except Exception as error:
                print(f"An error occurs while resetting LLMYearlyUsage.csv\n{error}")

        except Exception as error:
            print(f"An error occurs while generating LLM Usage Yearly Report\n{error}")

        previousYear = currentTime[4]

    # Checking new month
    if currentTime[1] != previousMonth:
        print(f"New Month Change: {previousMonth} -> {currentTime[1]}")
        try:
            print(f"Resetting LLMMonthlyUsage.csv...")
            print(f"Successfully resetting LLMMonthlyUsage.csv!")

            try:
                print(f"Creating a new month folder...")
                os.mkdir(f"{LLM_USAGE_LOG}{currentTime[4]}/{currentTime[1]}")
                print(f"Successfully create a new month folder!")

            except Exception as error:
                print(f"An error occurs while creating a new month folder\n{error}")

        except Exception as error:
            print(f"An error occurs while resetting LLMMonthlyUsage.csv\n{error}")
        previousMonth = currentTime[1]


@Emmanuel.event
async def on_ready():
    await Emmanuel.wait_until_ready()
    print(f"Logged in as {Emmanuel.user} (ID: {Emmanuel.user.id})")
    print("Knight Emmanuel is ONLINE!")

    #  Synced all commands -> Add new command if not already existed, else update the pre-existing command
    await Emmanuel.tree.sync()
    SynedCmds = await Emmanuel.tree.fetch_commands()
    for cmd in SynedCmds:
        print(f"Synced command /{cmd.name}")
    print(f"Commands are updated and ready to use!")
    print("\n\n")
    reset_user_uncensor_value_and_update_llm_usage.start()


@Emmanuel.event
async def on_member_join(member):
    await asyncio.sleep(1)
    serverID = member.guild.id
    print(f"Member {member.name} ID {member.id} join server {member.guild.name} ID {member.guild.id}\n\n")
    await checkServerExistInConfigFile(str(serverID))
    memberConfigInServer = configuration.get(str(serverID), {}).get("User-Uncensor-Limit", {}).get(str(member.id), "")
    if not memberConfigInServer:
        configuration[str(serverID)]["User-Uncensor-Limit"][str(member.id)] = DAILY_UNCENSOR_LIMIT
        async with ConfigLock:
            async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                await file.write(json.dumps(configuration, indent=4))


@Emmanuel.event
async def on_member_remove(member):
    serverID = member.guild.id
    if member.id == Emmanuel.user.id:
        print(f"Knight Emmanuel was kicked from server {member.guild.name} ID {member.guild.id}\n\n")
        if configuration.get(str(serverID), ""):
            del configuration[str(serverID)]
            print(f"Removed server ID {serverID} from Emmanuel Configuration!\n\n")
    else:
        await asyncio.sleep(1)
        print(f"Member {member.name} ID {member.id} left server {member.guild.name} ID {member.guild.id}\n\n")
        await checkServerExistInConfigFile(str(serverID))
        memberConfigInServer = configuration.get(str(serverID), {}).get("User-Uncensor-Limit", {}).get(str(member.id), "")
        if memberConfigInServer:
            del configuration[str(serverID)]["User-Uncensor-Limit"][str(member.id)]
    async with ConfigLock:
        async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
            await file.write(json.dumps(configuration, indent=4))


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="add_uncensored_member",
    description="Adding a server member to the uncensored list for this server!"
)
@app_commands.describe(member="Please mention a member in the server!")
@app_commands.guild_only()
async def add_uncensored_member(ctx, member: discord.Member):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
        await checkServerExistInConfigFile(str(ctx.guild.id))
        async with ConfigLock:
            if member.id not in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                configuration[str(ctx.guild.id)]["Uncensored-members"].append(member.id)
                async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                    await file.write(json.dumps(configuration, indent=4))
                print(f"Configuration file updated: {configuration}\n\n")
                await ctx.followup.send(f"{member.name} has been added to the white list!")
            else:
                await ctx.followup.send(f"{member.name} already added to the white list!")
    else:
        await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="remove_uncensored_member",
    description="Removing a server member off the uncensored list for this server!"
)
@app_commands.describe(member="Please mention a member in the server!")
@app_commands.guild_only()
async def remove_uncensored_member(ctx, member: discord.Member):
    if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
        await checkServerExistInConfigFile(str(ctx.guild.id))
        async with ConfigLock:
            if member.id not in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                await ctx.followup.send(f"{member.name} already removed from the white list!")
            else:
                configuration[str(ctx.guild.id)]["Uncensored-members"].remove(member.id)
                async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                    await file.write(json.dumps(configuration, indent=4))
                print(f"Configuration file updated: {configuration}\n\n")
                await ctx.followup.send(f"{member.name} has been removed from the white list!")
    else:
        await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="add_uncensored_channel",
    description="Adding a server channel to the uncensored list for this server!"
)
@app_commands.guild_only()
async def add_uncensored_channel(ctx):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
        await checkServerExistInConfigFile(str(ctx.guild.id))
        async with ConfigLock:
            if ctx.channel.id in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                await ctx.followup.send(f"{ctx.channel.name} already added to the uncensored list!")
            else:
                configuration[str(ctx.guild.id)]["Uncensored-channels"].append(ctx.channel.id)
                async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                    await file.write(json.dumps(configuration, indent=4))
                print(f"Configuration file updated: {configuration}\n\n")
                await ctx.followup.send(f"{ctx.channel.name} has been added from the white list!")
    else:
        await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="remove_uncensored_channel",
    description="Removing a server channel off the uncensored list for this server!"
)
@app_commands.guild_only()
async def remove_uncensored_channel(ctx):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
        await checkServerExistInConfigFile(str(ctx.guild.id))
        async with ConfigLock:
            if ctx.channel.id not in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                await ctx.followup.send(f"{ctx.channel.name} already removed from the uncensored list!")
            else:
                configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(ctx.channel.id)
                async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                    await file.write(json.dumps(configuration, indent=4))
                print(f"Configuration file updated: {configuration}\n\n")
                await ctx.followup.send(f"{ctx.channel.name} has been removed from the white list!")
    else:
        await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="uncensored_members",
    description="List all the member who are not being monitored by Emmanuel in the server")
@app_commands.guild_only()
async def uncensored_members(ctx):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
        await checkServerExistInConfigFile(str(ctx.guild.id))
        members = ""
        async with ConfigLock:
            for memberID in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                member = Emmanuel.get_user(memberID)
                if member:
                    members += f"Member ID: {member.id}\tMember name: {member.name}\n"
                else:
                    configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(memberID)
                    async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                        await file.write(json.dumps(configuration, indent=4))
            await ctx.followup.send(f"Uncensored members for server {ctx.guild.name} ID {ctx.guild.id}:\n{members}")
    else:
        await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="uncensored_channels",
    description="List all the channels not being monitored by Emmanuel in the server")
@app_commands.guild_only()
async def uncensored_channels(ctx):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
        await checkServerExistInConfigFile(str(ctx.guild.id))
        channels = ""
        async with ConfigLock:
            for channelID in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                channel = Emmanuel.get_channel(channelID)
                if channel:
                    channels += f"Channel ID: {channel.id}\tChannel name: {channel.name}\n"
                else:
                    configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(channelID)
                    async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                        await file.write(json.dumps(configuration, indent=4))
            await ctx.followup.send(f"Uncensored channels for server {ctx.guild.name} ID {ctx.guild.id}:\n{channels}")
    else:
        await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


@Emmanuel.tree.command(
    name="update_emmanuel_scan_database",
    description="Update Emmanuel scan database after the manual review of the content"
)
@app_commands.describe(sha_512="Provide the SHA512 hash", nsfw="Is the content NSFW or not?", reason="Provide a details reason")
async def update_emmanuel_scan_database(ctx, sha_512: str, nsfw: Literal["No", "Yes"], reason: str):
    await ctx.response.defer(ephemeral=True)
    contents =  PENDING_MANUAL_REVIEW_CONTENT.get(sha_512, [])
    if contents:
        hashes = [sha_512] + contents
        PENDING_MANUAL_REVIEW_CONTENT.pop(sha_512, None)
        for h in hashes:
            if nsfw == "No":
                await AddingNewCleanData(h, reason)
            else:
                await AddingNewNSFWData(h, reason)
        async with PendingReviewLock:
            async with aiofiles.open(PENDING_MANUAL_REVIEW_CONTENT, "w") as file:
                await file.write(json.dumps(PENDING_MANUAL_REVIEW_CONTENT, indent=4))
        await ctx.followup.send(f"The provided SHA-512 hash has been updated as {'clean' if nsfw == 'No' else 'NSFW'} in Emmanuel scan database!")
    else:
        await ctx.followup.send("There is no matching SHA-512 hash in Emmanuel pending manual review list!")


@Emmanuel.event
async def on_message_edit(before, after):  # Note: media attachment can be embedded via URL in re-edit message!
    if before.content != after.content:
        await EmmanuelScan(after, True, before)


@Emmanuel.event
async def on_message(message):
    await EmmanuelScan(message)
