import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyCsO2oMukVDoWTtrZ0JqvsmaRlLQZI4_Qo",
  authDomain: "quickqueue-aebb2.firebaseapp.com",
  projectId: "quickqueue-aebb2",
  storageBucket: "quickqueue-aebb2.firebasestorage.app",
  messagingSenderId: "133024707325",
  appId: "1:133024707325:web:493ffd9650e25a0c9d0494",
};

const app = initializeApp(firebaseConfig);

// ✅ SIMPLE + WORKS WITH EXPO
const auth = getAuth(app);
const db = getFirestore(app);

export { auth, db };
export default app;
