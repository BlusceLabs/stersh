import { useState } from "react";

export default function UserProfile() {
  const [name, setName] = useState("John Doe");
  const [email, setEmail] = useState("john@example.com");

  return (
    <div className="bg-gray-900 p-6 rounded-lg">
      <h3 className="text-xl font-bold mb-4">Account Settings</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-gray-400 mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="bg-gray-800 px-4 py-2 rounded w-full"
          />
        </div>
        <div>
          <label className="block text-gray-400 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="bg-gray-800 px-4 py-2 rounded w-full"
          />
        </div>
        <button className="bg-red-600 hover:bg-red-700 px-6 py-2 rounded">
          Save Changes
        </button>
      </div>
    </div>
  );
}