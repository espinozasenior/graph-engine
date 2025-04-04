/**
 * Sample JavaScript file for testing the TreeSitterParser.
 * 
 * This file contains various JavaScript constructs that should be detected
 * by the TreeSitterParser.
 */

// Import statement
const fs = require('fs');
const path = require('path');

// Class declaration
class Animal {
  constructor(name, type) {
    this.name = name;
    this.type = type;
  }
  
  makeSound() {
    console.log(`${this.name} makes a sound.`);
  }
  
  static createFromData(data) {
    return new Animal(data.name, data.type);
  }
}

// Class with inheritance
class Dog extends Animal {
  constructor(name, breed) {
    super(name, 'dog');
    this.breed = breed;
  }
  
  makeSound() {
    console.log(`${this.name} barks!`);
  }
  
  fetch() {
    console.log(`${this.name} fetches the ball.`);
  }
}

// Function declaration
function readJsonFile(filePath) {
  try {
    const data = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading file:', error);
    return null;
  }
}

// Arrow function
const writeJsonFile = (filePath, data) => {
  try {
    const jsonData = JSON.stringify(data, null, 2);
    fs.writeFileSync(filePath, jsonData, 'utf8');
    return true;
  } catch (error) {
    console.error('Error writing file:', error);
    return false;
  }
};

// Async function
async function processAnimals(dirPath) {
  try {
    const files = fs.readdirSync(dirPath);
    const jsonFiles = files.filter(file => path.extname(file) === '.json');
    
    const animals = [];
    
    for (const file of jsonFiles) {
      const filePath = path.join(dirPath, file);
      const data = readJsonFile(filePath);
      
      if (data) {
        if (data.type === 'dog') {
          const dog = new Dog(data.name, data.breed);
          animals.push(dog);
        } else {
          const animal = Animal.createFromData(data);
          animals.push(animal);
        }
      }
    }
    
    console.log(`Processed ${animals.length} animals`);
    return animals;
  } catch (error) {
    console.error('Error processing animals:', error);
    return [];
  }
}

// Object with methods
const AnimalUtils = {
  sortByName(animals) {
    return [...animals].sort((a, b) => a.name.localeCompare(b.name));
  },
  
  filterByType(animals, type) {
    return animals.filter(animal => animal.type === type);
  },
  
  getTypes(animals) {
    return [...new Set(animals.map(animal => animal.type))];
  }
};

// Main function call
(async function() {
  const animals = await processAnimals('./data');
  console.log('Types:', AnimalUtils.getTypes(animals));
  console.log('Dogs:', AnimalUtils.filterByType(animals, 'dog').length);
})().catch(error => {
  console.error('Main error:', error);
});

// Export
module.exports = {
  Animal,
  Dog,
  readJsonFile,
  writeJsonFile,
  processAnimals,
  AnimalUtils
}; 