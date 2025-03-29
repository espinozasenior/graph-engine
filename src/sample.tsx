/**
 * Sample TypeScript file for testing the TreeSitterParser.
 * 
 * This file contains various TypeScript constructs that should be detected
 * by the TreeSitterParser.
 */
import { useState, useEffect } from 'react';
import axios from 'axios';

// Interface definition
interface Person {
  name: string;
  age: number;
  email?: string;
}

// Type definition
type UserRole = 'admin' | 'editor' | 'viewer';

// Base class
abstract class BaseEntity {
  protected id: number;
  
  constructor(id: number) {
    this.id = id;
  }
  
  abstract display(): void;
  
  getId(): number {
    return this.id;
  }
}

// Class extending BaseEntity
class User extends BaseEntity {
  private name: string;
  private role: UserRole;
  
  constructor(id: number, name: string, role: UserRole = 'viewer') {
    super(id);
    this.name = name;
    this.role = role;
  }
  
  display(): void {
    console.log(`User ${this.name} (ID: ${this.id}) has role ${this.role}`);
  }
  
  hasAdminAccess(): boolean {
    return this.role === 'admin';
  }
}

// Function declaration
function calculateAge(birthYear: number): number {
  const currentYear = new Date().getFullYear();
  return currentYear - birthYear;
}

// Arrow function
const formatName = (firstName: string, lastName: string): string => {
  return `${lastName}, ${firstName}`;
};

// React functional component example
const UserProfile = ({ userId }: { userId: number }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  
  useEffect(() => {
    // Fetch user data
    const fetchUser = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`/api/users/${userId}`);
        const userData = response.data;
        setUser(new User(userData.id, userData.name, userData.role));
      } catch (error) {
        console.error('Error fetching user:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchUser();
  }, [userId]);
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  if (!user) {
    return <div>User not found</div>;
  }
  
  return (
    <div>
      <h1>User Profile</h1>
      <p>Name: {user.getName()}</p>
      <p>Role: {user.getRole()}</p>
      {user.hasAdminAccess() && (
        <button>Admin Settings</button>
      )}
    </div>
  );
};

export default UserProfile;
export { User, calculateAge, formatName }; 