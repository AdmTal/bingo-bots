# Bingo Bots

Bots that play online cash bingo.

> 🚫 **Disclaimer**: DO NOT TRY THIS, THESE GAMES ARE A TRAP, YOU CANNOT WIN!! This project is meant for educational
> purposes only. Please don’t gamble. Even with a fancy bot, the odds are still worse than 50/50. Instead, dive into the
> world of coding—it's much more rewarding. Still reading? Consider exploring more programming adventures or perhaps
> even [buying my book](https://github.com/AdmTal/emoji-puzzles).

Ever wondered if bots could change the odds of online cash bingo games? Well, they can't! Even with the assistance of a
bot, these games prove to be unwinnable. This Python project showcases two bots I created for fun to play the "Bingo
King" and "Bingo Cash" games on a real iPad Pro 10.5.

## Demo Videos

Watch the bots in action 🤖

### Bingo King

https://github.com/AdmTal/bingo-bots/assets/3382568/cd1ec309-8d6e-4749-8f87-afd00e03734e

### Bingo Cash

https://github.com/AdmTal/bingo-bots/assets/3382568/a2df991c-d8f1-4c21-8035-9457f84b33ea

### Game Support:

Currently, this project supports:

- [Bingo King](https://apps.apple.com/us/app/bingo-king-win-real-money/id1539845099) - Promo code for some free playing
  cash: `DFEAiCJB`
- [Bingo Cash](https://apps.apple.com/us/app/bingo-cash/id1522266397) - Promo code: `ZKGP34 `

**Note**: Using the promo codes helps both you and me! 🎉

## Getting Started

### Requirements:

- **Python 3.9** with Pip + virtualenv.
- **Tesseract** for OCR.
- **WebDriverAgent**. Please note, I don't use Appium, only the WebDriverAgent. To set it up:
    1. Clone the WebDriverAgent from [here](https://github.com/facebookarchive/WebDriverAgent/).
    2. Build and deploy the WebDriverAgent using Xcode. Replace the iPad ID in the command below with yours. If you need
       more information about WebDriverAgent
       setup, [this archived page](https://github.com/facebookarchive/WebDriverAgent/) might help.

```
cd /usr/local/lib/node_modules/appium-webdriveragent && \
   xcodebuild build-for-testing test-without-building \
   -project WebDriverAgent.xcodeproj \
   -scheme WebDriverAgentRunner \
   -destination "id=YOUR_IPAD_ID" \
   -allowProvisioningUpdates
```

### Installation:

1. Clone this repository.
2. Create a virtual environment: `python3 -m venv myenv`
3. Activate the virtual environment: `source myenv/bin/activate` (on macOS/Linux) or `myenv\Scripts\activate` (on
   Windows).
4. Install the required Python packages: `pip install -r requirements.txt`

### Running the Bots:

1. Launch the WebDriverAgent on the iPad—it should display a URL upon launch.
2. Execute the main script with the provided URL:

```
python main.py <URL_FROM_WEBDRIVERAGENT>
```

## Technical Insights:

- Tailored specifically for **iPad Pro 10.5**. You'd need to adjust hardcoded pixel coordinates for other devices.
- The bots are built on the principle of capturing screenshots on the iPad and using OCR (Tesseract) to decipher
  numbers.
- Speed can be enhanced by using `vmtouch` to preload the Tesseract binary—a potential time saver of about a quarter of
  a second per number read.
- Everything ran smoothly on a MacBook Air.
- Many clones of these bingo games exist. With slight adjustments, the logic used here might work on other similar
  games.

## Final Thoughts:

Please remember, gambling is not a solution, and the odds are never truly in your favor. Dive deep into programming—it's
both fun and enlightening! And as always, stay curious! 🚀