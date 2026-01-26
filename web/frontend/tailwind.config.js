/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        paranormal: {
          ghost: '#9b59b6',
          shadow: '#2c3e50',
          cryptid: '#27ae60',
          ufo: '#3498db',
          alien: '#1abc9c',
          haunting: '#8e44ad',
          poltergeist: '#e74c3c',
          precognition: '#f39c12',
          nde: '#e67e22',
          obe: '#16a085',
          timeslip: '#2980b9',
          doppelganger: '#c0392b',
          sleepparalysis: '#7f8c8d',
          possession: '#d35400',
          other: '#95a5a6',
        }
      }
    },
  },
  plugins: [],
}
