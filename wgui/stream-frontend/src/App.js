import logo from './logo.svg';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <p>
          <div>
          Flux Maps
          <br/>
          <img alt="flux" style={{width:"800px"}} src="http://localhost:5000/stream?prefix=flux"></img>
          </div>
          <div>
          Slope Maps
          <br/>
          <img alt="flux" style={{width:"800px"}} src="http://localhost:5000/stream?prefix=slopemap"></img>
          </div>
        </p>
      </header>
    </div>
  );
}

export default App;
