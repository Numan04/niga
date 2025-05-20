import aiohttp
import asyncio
from colorama import init, Fore
import random
import time

# Initialize colorama for colored output
init(autoreset=True)

# Function to load proxies from proxy.txt
def load_proxies(file_path):
    try:
        with open(file_path, 'r') as f:
            proxies = f.readlines()
        # Strip any extra spaces or newline characters
        return [proxy.strip() for proxy in proxies]
    except FileNotFoundError:
        print(f"{Fore.RED}[ERROR] Proxy file {file_path} not found.")
        return []

# Function to save valid invite codes to a new text file
def save_valid_invites(valid_invites):
    with open("valid_invites.txt", 'a') as file:
        for invite in valid_invites:
            file.write(f"{invite}\n")
    print(f"{Fore.GREEN}[INFO] Valid invites have been saved to valid_invites.txt")

# Function to check if an invite is valid using asynchronous requests with proxy
async def check_invite(session, invite_code, proxies, semaphore, valid_invites):
    url = f"https://discord.com/api/v9/invites/{invite_code}"
    
    # Randomly choose a proxy from the list
    proxy = random.choice(proxies)

    try:
        async with semaphore:
            async with session.get(url, proxy=f"http://{proxy}") as response:
                if response.status == 200:
                    invite_data = await response.json()
                    print(f"{Fore.GREEN}[VALID] Invite {invite_code} is valid! Server: {invite_data['guild']['name']}")
                    valid_invites.append(invite_code)  # Add valid invite to the list
                elif response.status == 404:
                    print(f"{Fore.RED}[INVALID] Invite {invite_code} is invalid (404).")
                elif response.status == 429:
                    # Handle rate limiting: the server tells us to wait before retrying
                    reset_time = int(response.headers.get('X-RateLimit-Reset', time.time()))
                    wait_time = reset_time - time.time() + 1  # Wait until the reset time
                    print(f"{Fore.YELLOW}[RATE LIMIT] Hit rate limit for invite {invite_code}. Retrying in {wait_time:.2f} seconds.")
                    await asyncio.sleep(wait_time)
                    await check_invite(session, invite_code, proxies, semaphore, valid_invites)  # Retry the request after waiting
                else:
                    print(f"{Fore.YELLOW}[ERROR] Error with invite {invite_code}: {response.status}")
    except aiohttp.ClientError as e:
        print(f"{Fore.RED}[ERROR] Request failed for {invite_code}: {e}")

# Function to handle reading from file and making concurrent requests
async def check_invites_from_file(file_path, proxies, semaphore, valid_invites):
    try:
        with open(file_path, 'r') as file:
            invite_codes = file.readlines()

        # Clean up the codes by stripping any extra spaces or newlines
        invite_codes = [code.strip() for code in invite_codes]

        async with aiohttp.ClientSession() as session:
            tasks = [check_invite(session, invite_code, proxies, semaphore, valid_invites) for invite_code in invite_codes]
            # Run the tasks concurrently with the limit imposed by semaphore
            await asyncio.gather(*tasks)

        # Save valid invites to a file after checking all
        save_valid_invites(valid_invites)

    except FileNotFoundError:
        print(f"{Fore.RED}[ERROR] File {file_path} not found.")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] An unexpected error occurred: {e}")

# Start the event loop and check invites
async def main():
    proxies = load_proxies('proxy.txt')  # Load proxies from proxy.txt
    valid_invites = []  # List to store valid invites
    if proxies:
        # Increase concurrency (e.g., 50 concurrent requests)
        semaphore = asyncio.Semaphore(50)
        await check_invites_from_file('invites.txt', proxies, semaphore, valid_invites)

# Run the script
if __name__ == "__main__":
    asyncio.run(main())
