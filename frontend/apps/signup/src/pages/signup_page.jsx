import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  MapPin,
  ArrowRight,
  LocateFixed,
  Store,
  Check,
  Truck,
} from "lucide-react";
import { read, write } from "../../../../shared/store";
import "../styles/signup_page.css";
export default function Signup({ navigate }) {
  const saved = read("merchant", null);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    businessName: "",
    owner: "",
    phone: "",
    type: "Retail shop",
    city: "Nairobi",
    address: "",
    ...saved,
  });
  const [point, setPoint] = useState(saved?.point || null);
  const [error, setError] = useState("");
  const [locating, setLocating] = useState(false);
  const [mapError, setMapError] = useState(false);
  const mapElement = useRef();
  const map = useRef();
  const marker = useRef();
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useEffect(() => {
    if (step !== 2) return;
    const instance = L.map(mapElement.current).setView(
      point ? [point.lat, point.lng] : [-1.286389, 36.817223],
      13,
    );
    map.current = instance;
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    })
      .on("tileerror", () => setMapError(true))
      .addTo(instance);
    const pin = L.divIcon({
      className: "business-pin",
      html: "<span></span>",
      iconSize: [24, 24],
      iconAnchor: [12, 24],
    });
    function select(latlng) {
      if (marker.current) marker.current.setLatLng(latlng);
      else
        marker.current = L.marker(latlng, { icon: pin, draggable: true })
          .addTo(instance)
          .on("dragend", (e) =>
            setPoint({
              lat: e.target.getLatLng().lat,
              lng: e.target.getLatLng().lng,
            }),
          );
      setPoint({ lat: latlng.lat, lng: latlng.lng });
    }
    instance.on("click", (e) => select(e.latlng));
    if (point) select(L.latLng(point.lat, point.lng));
    instance.on("select-location", (e) => select(e.latlng));
    return () => {
      instance.remove();
      map.current = null;
      marker.current = null;
    };
  }, [step]);
  const field = (name, value) => setForm({ ...form, [name]: value });
  function submit(e) {
    e.preventDefault();
    setError("");
    if (step === 1) {
      if (
        !form.businessName.trim() ||
        !form.owner.trim() ||
        !/^\+?[0-9 ()-]{7,20}$/.test(form.phone)
      ) {
        setError(
          "Enter a business name, contact name, and valid phone number.",
        );
        return;
      }
      setStep(2);
      return;
    }
    if (!point) {
      setError(
        "Choose your delivery point on the map, or enter coordinates below.",
      );
      return;
    }
    if (!form.address.trim() || !form.city.trim()) {
      setError("Add your town and delivery directions.");
      return;
    }
    try {
      write("merchant", {
        ...form,
        businessName: form.businessName.trim(),
        city: form.city.trim(),
        point,
      });
      navigate("/orders");
    } catch {
      setError(
        "Your profile could not be saved. Please enable browser local storage.",
      );
    }
  }
  function locate() {
    setError("");
    if (!navigator.geolocation) {
      setError("Location is unavailable. Select a point on the map.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (!alive.current) return;
        const latlng = L.latLng(pos.coords.latitude, pos.coords.longitude);
        map.current?.setView(latlng, 16);
        map.current?.fire("select-location", { latlng });
        setLocating(false);
      },
      () => {
        if (alive.current) {
          setLocating(false);
          setError(
            "Could not access your location. Select the map or enter coordinates instead.",
          );
        }
      },
      { timeout: 10000 },
    );
  }
  return (
    <div className="page signup-page">
      <div className="eyebrow">LET’S BUILD YOUR BUSINESS TOGETHER</div>
      <h1>
        {saved
          ? "Your business, at a glance."
          : "A better way to keep your shelves full."}
      </h1>
      <p className="muted">
        Tell us a little about your business. We’ll take care of the heavy
        lifting.
      </p>
      <div className="signup-layout">
        <section className="card signup-form">
          <div className="signup-steps">
            <span className={step === 1 ? "current" : ""}>
              <b>{step > 1 ? <Check size={14} /> : 1}</b> Business details
            </span>
            <i />
            <span className={step === 2 ? "current" : ""}>
              <b>2</b> Delivery location
            </span>
          </div>
          <h2>
            {step === 1
              ? "First, meet your business."
              : "Where should we deliver?"}
          </h2>
          <p className="muted form-intro">
            {step === 1
              ? "A few details to make your first order feel effortless."
              : "Pin your doorstep so your stock arrives at the right place."}
          </p>
          <form onSubmit={submit}>
            {step === 1 ? (
              <>
                <label className="field">
                  Business name
                  <input
                    required
                    maxLength={100}
                    autoComplete="organization"
                    placeholder="e.g. Wanjiku’s Mini Market"
                    value={form.businessName}
                    onChange={(e) => field("businessName", e.target.value)}
                  />
                </label>
                <div className="fields">
                  <label className="field">
                    Contact name
                    <input
                      required
                      maxLength={100}
                      autoComplete="name"
                      placeholder="Your full name"
                      value={form.owner}
                      onChange={(e) => field("owner", e.target.value)}
                    />
                  </label>
                  <label className="field">
                    Phone number
                    <input
                      required
                      type="tel"
                      autoComplete="tel"
                      placeholder="e.g. 0712 345 678"
                      value={form.phone}
                      onChange={(e) => field("phone", e.target.value)}
                    />
                  </label>
                </div>
                <label className="field">
                  Business type
                  <select
                    value={form.type}
                    onChange={(e) => field("type", e.target.value)}
                  >
                    {[
                      "Retail shop",
                      "Restaurant / café",
                      "Hotel",
                      "Office",
                      "Wholesaler",
                      "Other",
                    ].map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </label>
                <p className="notice">
                  This demo saves your business profile in this browser. No
                  password is needed yet.
                </p>
              </>
            ) : (
              <>
                <div className="row map-heading">
                  <strong>
                    <MapPin size={16} /> Delivery pin
                  </strong>
                  <button
                    className="btn small"
                    type="button"
                    disabled={locating}
                    onClick={locate}
                  >
                    <LocateFixed size={14} />
                    {locating ? "Locating…" : "Use my location"}
                  </button>
                </div>
                <div
                  className="location-map"
                  ref={mapElement}
                  aria-label="OpenStreetMap delivery location selector"
                />
                {mapError && (
                  <p className="notice">
                    Map tiles could not load. You can still enter coordinates
                    below.
                  </p>
                )}
                <p className="map-caption">
                  Click the map to drop a pin. Drag it to your exact doorstep.
                </p>
                <div className="fields coordinate-fields">
                  {[
                    ["lat", "Latitude", -90, 90],
                    ["lng", "Longitude", -180, 180],
                  ].map(([key, label, min, max]) => (
                    <label className="field" key={key}>
                      {label}
                      <input
                        type="number"
                        step="any"
                        min={min}
                        max={max}
                        required
                        value={point?.[key] ?? ""}
                        onChange={(e) => {
                          const value = e.target.value;
                          if (value === "") {
                            setPoint(null);
                            return;
                          }
                          const next = {
                            lat: point?.lat ?? -1.286389,
                            lng: point?.lng ?? 36.817223,
                            [key]: Number(value),
                          };
                          setPoint(next);
                          if (
                            next.lat >= -90 &&
                            next.lat <= 90 &&
                            next.lng >= -180 &&
                            next.lng <= 180
                          ) {
                            map.current?.fire("select-location", {
                              latlng: L.latLng(next.lat, next.lng),
                            });
                            map.current?.panTo([next.lat, next.lng]);
                          }
                        }}
                      />
                    </label>
                  ))}
                </div>
                <label className="field">
                  City / town
                  <input
                    required
                    maxLength={100}
                    autoComplete="address-level2"
                    value={form.city}
                    onChange={(e) => field("city", e.target.value)}
                  />
                </label>
                <label className="field">
                  Street, building & delivery directions
                  <textarea
                    required
                    maxLength={500}
                    rows={2}
                    placeholder="e.g. Moi Avenue, next to the pharmacy, ground floor"
                    value={form.address}
                    onChange={(e) => field("address", e.target.value)}
                  />
                </label>
              </>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <div className="row signup-actions">
              {step === 2 && (
                <button
                  type="button"
                  className="btn"
                  onClick={() => setStep(1)}
                >
                  Back
                </button>
              )}
              <button type="submit" className="btn primary">
                {step === 1 ? "Continue to location" : "Save & start shopping"}
                <ArrowRight size={16} />
              </button>
            </div>
          </form>
        </section>
        <aside className="signup-aside">
          <div className="onboard-illustration">
            <Store size={70} strokeWidth={1} />
            <span>YOUR BUSINESS. OUR PRIORITY.</span>
          </div>
          <h2>
            Less running around.
            <br />
            More running your business.
          </h2>
          <p className="muted">
            From the essentials you sell to the supplies you use, get everything
            you need in one place.
          </p>
          <div className="onboard-benefit">
            <span>
              <Check size={17} />
            </span>
            <div>
              <strong>Prices that work for you</strong>
              <p>Wholesale value on everyday essentials.</p>
            </div>
          </div>
          <div className="onboard-benefit">
            <span>
              <Truck size={17} />
            </span>
            <div>
              <strong>From our shelves to yours</strong>
              <p>Convenient delivery to your business.</p>
            </div>
          </div>
          <div className="onboard-benefit">
            <span>
              <MapPin size={17} />
            </span>
            <div>
              <strong>Right to your doorstep</strong>
              <p>A precise location for a smoother delivery.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
