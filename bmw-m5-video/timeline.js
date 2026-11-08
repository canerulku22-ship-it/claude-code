// Shared by film.html (captions, scene timing), audio.py and voiceover.mjs.
// `text` is the on-screen caption, `say` is what the narrator pronounces,
// `at` is the start time in seconds. Must stay valid JSON inside the braces.
window.TIMELINE = {
  "duration": 41.5,
  "voice": "bf_emma",
  "speed": 1.08,
  "vo": [
    { "id": "01", "cap": false, "at": 0.25, "text": "This is why the BMW M5 is the best car on British roads.", "say": "This is why the B M W M five is the best car on British roads." },
    { "id": "02", "at": 4.9, "text": "Since 1984, it’s put supercar power in a family saloon.", "say": "Since nineteen eighty-four, it's put supercar power in a family saloon." },
    { "id": "03", "at": 9.3, "text": "The new one? A twin-turbo V8 and an electric motor.", "say": "The new one? A twin-turbo V eight, and an electric motor." },
    { "id": "04", "cap": false, "at": 12.75, "text": "727 horsepower.", "say": "Seven hundred and twenty-seven horsepower." },
    { "id": "05", "cap": false, "at": 15.6, "text": "0–62 in 3.5 seconds.", "say": "Nought to sixty-two, in three and a half seconds." },
    { "id": "06", "at": 18.9, "text": "But here’s the clever bit: it plugs in.", "say": "But here's the clever bit. It plugs in." },
    { "id": "07", "at": 21.7, "text": "Up to 43 miles on electric alone. Most commutes, there and back, with no petrol.", "say": "Up to forty-three miles on electric alone. Most commutes, there and back, with no petrol." },
    { "id": "08", "at": 27.4, "text": "Lower company-car tax. All-wheel drive for British weather.", "say": "Lower company car tax. All-wheel drive, for British weather." },
    { "id": "09", "cap": false, "at": 31.7, "text": "Saloon, or Touring.", "say": "Saloon, or Touring." },
    { "id": "10", "cap": false, "at": 34.0, "text": "Electric on Monday. V8 on Saturday.", "say": "Electric on Monday. V eight on Saturday." },
    { "id": "11", "cap": false, "at": 37.6, "text": "The BMW M5.", "say": "The B M W M five." }
  ]
};
